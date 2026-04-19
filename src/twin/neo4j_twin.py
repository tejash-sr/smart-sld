"""Neo4j-based Digital Twin infrastructure for real-time topology state."""
from __future__ import annotations
import json
import uuid
from datetime import datetime
from typing import Optional
from neo4j import GraphDatabase, ManagedTransaction
from neo4j.exceptions import DriverError
import logging

logger = logging.getLogger(__name__)


class Neo4jTwin:
    """Digital Twin: Maintains live topology state in Neo4j."""
    
    def __init__(self, uri: str = "bolt://localhost:7687", 
                 username: str = "neo4j", 
                 password: str = "password"):
        """Initialize Neo4j connection."""
        try:
            self.driver = GraphDatabase.driver(uri, auth=(username, password))
            self.driver.verify_connectivity()
            logger.info(f"✅ Connected to Neo4j at {uri}")
        except DriverError as e:
            logger.warning(f"⚠️ Neo4j connection failed: {e}")
            logger.warning("⚠️ Will attempt to start Neo4j automatically...")
            self._try_start_neo4j()
            self.driver = GraphDatabase.driver(uri, auth=(username, password))
            
    def _try_start_neo4j(self):
        """Attempt to start Neo4j if not running."""
        import subprocess
        import platform
        try:
            os_type = platform.system()
            if os_type == "Windows":
                # Windows: use neo4j.bat
                subprocess.run(["neo4j", "start"], check=False)
            else:
                # Linux/Mac: use systemctl or direct command
                subprocess.run(["neo4j", "start"], check=False)
        except Exception as e:
            logger.error(f"Could not auto-start Neo4j: {e}")
    
    def close(self):
        """Close driver."""
        self.driver.close()
    
    def clear_all(self):
        """Delete all nodes and relationships (for fresh start)."""
        with self.driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")
            logger.info("✅ Cleared all Neo4j data")
    
    def ingest_topology(self, extracted_sld: dict, batch_id: str | None = None) -> str:
        """
        Ingest ExtractedSLD into Neo4j as a living graph.
        Returns the batch_id.
        """
        batch_id = batch_id or str(uuid.uuid4())[:8]
        
        with self.driver.session() as session:
            # Create batch node
            session.run(
                """
                CREATE (b:Batch {
                    id: $batch_id,
                    timestamp: datetime.realtime(),
                    source: $source,
                    voltage_levels: $voltages,
                    component_count: $comp_count
                })
                """,
                batch_id=batch_id,
                source=extracted_sld.get("source_filename", "unknown"),
                voltages=extracted_sld.get("voltage_levels", []),
                comp_count=len(extracted_sld.get("components", []))
            )
            
            # Create component nodes
            for comp in extracted_sld.get("components", []):
                session.run(
                    """
                    CREATE (c:Component {
                        id: $comp_id,
                        type: $comp_type,
                        label: $label,
                        voltage: $voltage,
                        x: $x,
                        y: $y,
                        confidence: $confidence
                    })
                    """,
                    comp_id=comp.get("id"),
                    comp_type=comp.get("component_type"),
                    label=comp.get("label", ""),
                    voltage=comp.get("voltage_level", ""),
                    x=comp.get("position", {}).get("x", 0),
                    y=comp.get("position", {}).get("y", 0),
                    confidence=comp.get("confidence", 0.0)
                )
            
            # Create connection edges
            for conn in extracted_sld.get("connections", []):
                session.run(
                    """
                    MATCH (a:Component {id: $from}), (b:Component {id: $to})
                    CREATE (a)-[r:CONNECTS_TO {
                        connection_type: $conn_type,
                        distance: $distance
                    }]->(b)
                    """,
                    **{
                        "from": conn.get("from_component"),
                        "to": conn.get("to_component"),
                        "conn_type": conn.get("connection_type", "direct"),
                        "distance": conn.get("distance", 0)
                    }
                )
            
            # Create bus sections
            for bus in extracted_sld.get("buses", []):
                session.run(
                    """
                    CREATE (b:Bus {
                        id: $bus_id,
                        name: $bus_name,
                        voltage: $voltage,
                        component_count: size($comp_ids)
                    })
                    """,
                    bus_id=bus.get("id"),
                    bus_name=bus.get("name"),
                    voltage=bus.get("voltage_level"),
                    comp_ids=bus.get("component_ids", [])
                )
        
        logger.info(f"✅ Ingested topology batch {batch_id} into Neo4j")
        return batch_id
    
    def get_topology(self) -> dict:
        """Get current topology as JSON (all nodes and edges)."""
        with self.driver.session() as session:
            nodes = session.run(
                "MATCH (c:Component) RETURN c.id as id, c.type as type, "
                "c.label as label, c.voltage as voltage, c.x as x, c.y as y"
            ).data()
            
            edges = session.run(
                "MATCH (a:Component)-[r:CONNECTS_TO]->(b:Component) "
                "RETURN a.id as from, b.id as to, r.connection_type as type"
            ).data()
            
            return {"components": nodes, "connections": edges}
    
    def query_graph(self, question: str) -> dict:
        """
        Execute a natural language question about the graph.
        (Will be called by LLM agent to convert questions into Cypher)
        """
        # This will be populated by the LangChain agent
        # For now, return structure query examples
        examples = {
            "buses": "MATCH (b:Bus) RETURN b.name, b.voltage, size(b.component_ids)",
            "feeders": "MATCH (c:Component) WHERE c.type='feeder' RETURN c",
            "connected_to": "MATCH (a:Component)-[*]->(b:Component) RETURN DISTINCT paths()"
        }
        return {"query_type": "graph_traversal", "examples": examples}
    
    def detect_anomalies(self) -> list[dict]:
        """Detect topology anomalies."""
        anomalies = []
        
        with self.driver.session() as session:
            # Detect floating buses (buses with no connections)
            floating = session.run(
                """
                MATCH (b:Bus)
                WHERE NOT (b:Bus)-[:CONTAINS]-()
                RETURN b.id as bus_id, b.name as bus_name
                """
            ).data()
            
            for item in floating:
                anomalies.append({
                    "type": "floating_bus",
                    "severity": "critical",
                    "object_id": item["bus_id"],
                    "description": f"Bus {item['bus_name']} has no connections",
                    "timestamp": datetime.utcnow().isoformat()
                })
            
            # Detect high-degree nodes (potential bottlenecks)
            high_degree = session.run(
                """
                MATCH (c:Component)
                WITH c, size((c)-[]-()) as degree
                WHERE degree > 5
                RETURN c.id as comp_id, c.label as label, degree
                ORDER BY degree DESC
                """
            ).data()
            
            for item in high_degree:
                anomalies.append({
                    "type": "bottleneck_node",
                    "severity": "warning",
                    "object_id": item["comp_id"],
                    "description": f"Component {item['label']} has {item['degree']} connections (potential bottleneck)",
                    "timestamp": datetime.utcnow().isoformat()
                })
        
        return anomalies
    
    def get_connected_to_bus(self, bus_name: str) -> dict:
        """Query: What's connected to a specific bus?"""
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (b:Bus {name: $bus})
                OPTIONAL MATCH (b)-[:CONTAINS]->(c:Component)
                OPTIONAL MATCH (c)-[r:CONNECTS_TO]->(other:Component)
                RETURN DISTINCT c as component, 
                       collect(DISTINCT other.label) as neighbors,
                       count(DISTINCT other) as neighbor_count
                """,
                bus=bus_name
            ).data()
            
            return {
                "bus": bus_name,
                "components": result
            }
