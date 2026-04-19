"""LangChain-based Agentic Fault Intelligence system using Ollama local LLM."""
from __future__ import annotations
import json
import logging
from typing import Optional
import networkx as nx
from datetime import datetime

logger = logging.getLogger(__name__)


class FaultIntelligenceAgent:
    """
    Multi-reasoning agent for fault analysis using local LLM.
    - Traces fault paths through topology graph
    - Suggests isolation points
    - Estimates restoration time
    - Provides risk assessment
    """
    
    def __init__(self, graph_dict: dict | None = None):
        """
        Initialize fault agent.
        
        Args:
            graph_dict: Topology as {"components": [...], "connections": [...]}
        """
        self.graph_dict = graph_dict or {}
        self.topology_graph = self._build_networkx_graph()
        self.isolation_history = []
        
        # LLM model info (will use Ollama)
        self.llm_provider = "ollama"
        self.model_name = "llama2"  # or "mistral"
        
        logger.info(f"✅ Fault Intelligence Agent initialized with {len(self.topology_graph.nodes)} nodes")
    
    def _build_networkx_graph(self) -> nx.DiGraph:
        """Build NetworkX graph from topology dict."""
        if not self.graph_dict:
            return nx.DiGraph()
        
        G = nx.DiGraph()
        
        # Add nodes
        for comp in self.graph_dict.get("components", []):
            G.add_node(comp["id"], **{
                "type": comp.get("type"),
                "label": comp.get("label", ""),
                "voltage": comp.get("voltage", ""),
                "x": comp.get("x", 0),
                "y": comp.get("y", 0)
            })
        
        # Add edges
        for conn in self.graph_dict.get("connections", []):
            G.add_edge(
                conn["from"],
                conn["to"],
                connection_type=conn.get("type", "direct")
            )
        
        return G
    
    def analyze_fault(self, fault_location: str, 
                     isolation_strategy: str = "optimal") -> dict:
        """
        Comprehensive fault analysis with multi-step reasoning.
        
        Args:
            fault_location: Component ID where fault occurred
            isolation_strategy: "optimal", "conservative", "aggressive"
            
        Returns:
            dict with analysis, isolation points, restoration estimate
        """
        
        if fault_location not in self.topology_graph.nodes:
            return {"error": f"Invalid fault location: {fault_location}"}
        
        analysis = {
            "fault_location": fault_location,
            "timestamp": datetime.utcnow().isoformat(),
            "strategy": isolation_strategy,
            
            # Step 1: Trace propagation
            "propagation_trace": self._trace_fault_propagation(fault_location),
            
            # Step 2: Identify isolation points
            "isolation_points": self._identify_isolation_points(
                fault_location, isolation_strategy
            ),
            
            # Step 3: Estimate impact
            "impact_assessment": self._assess_impact(fault_location),
            
            # Step 4: Estimate restoration
            "restoration_estimate": self._estimate_restoration_time(
                fault_location, analysis
            ),
            
            # Step 5: Risk assessment
            "risk_assessment": self._assess_risks(fault_location),
        }
        
        # Multi-turn reasoning (simulated with rules - would use LLM in production)
        analysis["agent_reasoning"] = self._generate_reasoning(analysis)
        
        return analysis
    
    def _trace_fault_propagation(self, source: str) -> dict:
        """Trace how fault propagates through network."""
        affected = set()
        paths = {}
        
        try:
            # BFS from fault point
            for target in self.topology_graph.nodes:
                if target == source:
                    continue
                
                try:
                    path = nx.shortest_path(self.topology_graph, source, target)
                    affected.add(target)
                    paths[target] = path
                except nx.NetworkXNoPath:
                    pass
        except Exception as e:
            logger.error(f"Error in fault propagation: {e}")
        
        # Categorize affected components
        feeders_affected = []
        buses_affected = []
        transformers_affected = []
        
        for comp_id in affected:
            comp_type = self.topology_graph.nodes[comp_id].get("type", "")
            label = self.topology_graph.nodes[comp_id].get("label", "")
            
            if "feeder" in comp_type.lower():
                feeders_affected.append({
                    "id": comp_id,
                    "label": label,
                    "distance_hops": len(paths.get(comp_id, []))
                })
            elif "bus" in comp_type.lower():
                buses_affected.append({
                    "id": comp_id,
                    "label": label,
                    "distance_hops": len(paths.get(comp_id, []))
                })
            elif "transformer" in comp_type.lower():
                transformers_affected.append({
                    "id": comp_id,
                    "label": label,
                    "distance_hops": len(paths.get(comp_id, []))
                })
        
        return {
            "total_affected": len(affected),
            "feeders_affected": len(feeders_affected),
            "buses_affected": len(buses_affected),
            "transformers_affected": len(transformers_affected),
            "affected_components": {
                "feeders": feeders_affected,
                "buses": buses_affected,
                "transformers": transformers_affected
            }
        }
    
    def _identify_isolation_points(self, fault_location: str, 
                                   strategy: str) -> list[dict]:
        """Identify optimal points to isolate the fault."""
        isolation_points = []
        
        # Find all predecessors (upstream elements)
        predecessors = list(self.topology_graph.predecessors(fault_location))
        
        if not predecessors:
            return [{
                "component_id": fault_location,
                "isolation_type": "source_isolation",
                "reason": "Fault source itself - must be immediately disconnected"
            }]
        
        for pred_id in predecessors:
            pred_data = self.topology_graph.nodes[pred_id]
            
            # Scoring for isolation point priority
            score = self._score_isolation_point(pred_id, fault_location, strategy)
            
            isolation_points.append({
                "component_id": pred_id,
                "component_label": pred_data.get("label", ""),
                "component_type": pred_data.get("type", ""),
                "isolation_priority": score["priority"],
                "reason": score["reason"],
                "affected_customers": score["affected_customers"],
                "risk_if_delayed": score["risk_if_delayed"]
            })
        
        # Sort by priority
        isolation_points.sort(key=lambda x: x["isolation_priority"], reverse=True)
        
        return isolation_points
    
    def _score_isolation_point(self, component_id: str, fault_location: str,
                               strategy: str) -> dict:
        """Score an isolation point for effectiveness."""
        comp_data = self.topology_graph.nodes[component_id]
        comp_type = comp_data.get("type", "").lower()
        
        # Count downstream loads
        try:
            descendants = nx.descendants(self.topology_graph, component_id)
        except:
            descendants = set()
        
        affected_loads = sum(1 for d in descendants 
                           if "load" in self.topology_graph.nodes[d].get("type", "").lower())
        
        # Strategy-based scoring
        if strategy == "optimal":
            # Minimize affected loads
            priority = 100 - (affected_loads * 5)
        elif strategy == "conservative":
            # Isolate at closest point to fault
            priority = 80 - len(nx.shortest_path(self.topology_graph, component_id, fault_location))
        elif strategy == "aggressive":
            # Isolate at highest-level point (fewest affected)
            if "breaker" in comp_type or "switch" in comp_type:
                priority = 90
            else:
                priority = 60
        else:
            priority = 50
        
        return {
            "priority": priority,
            "reason": f"{comp_type} at {comp_data.get('label')} - affects {affected_loads} loads",
            "affected_customers": affected_loads,
            "risk_if_delayed": "High" if affected_loads > 10 else "Medium" if affected_loads > 5 else "Low"
        }
    
    def _assess_impact(self, fault_location: str) -> dict:
        """Assess immediate and cascading impact."""
        propagation = self._trace_fault_propagation(fault_location)
        
        return {
            "immediate_outage": f"{propagation['feeders_affected']} feeders, {propagation['buses_affected']} buses",
            "total_affected_components": propagation["total_affected"],
            "cascading_risk": "High" if propagation["total_affected"] > 20 else "Medium" if propagation["total_affected"] > 10 else "Low",
            "critical_infrastructure_affected": len([x for x in propagation["affected_components"]["buses"] if "critical" in x.get("label", "").lower()]) > 0
        }
    
    def _estimate_restoration_time(self, fault_location: str, analysis: dict) -> dict:
        """Estimate time to restore service."""
        fault_type = "unknown"
        fault_data = self.topology_graph.nodes.get(fault_location, {})
        
        if "transformer" in fault_data.get("type", "").lower():
            # Transformers take longer
            base_time = 120  # minutes
            fault_type = "transformer"
        elif "breaker" in fault_data.get("type", "").lower():
            # Breaker faults can be quick
            base_time = 15
            fault_type = "breaker"
        elif "line" in fault_data.get("type", "").lower():
            # Line damages vary
            base_time = 60
            fault_type = "line_damage"
        else:
            base_time = 45
        
        # Adjust based on isolation complexity
        isolation_points = analysis["isolation_points"]
        if len(isolation_points) > 3:
            base_time += 30  # More complex
        
        return {
            "fault_type": fault_type,
            "estimated_time_minutes": base_time,
            "best_case_minutes": base_time // 2,
            "worst_case_minutes": base_time * 2,
            "restoration_steps": [
                "1. Isolate affected section",
                "2. Verify fault location (if needed)",
                "3. Repair or replace component",
                "4. Test safety protocols",
                "5. Restore service gradually (avoid inrush)",
                "6. Monitor for recurrence"
            ]
        }
    
    def _assess_risks(self, fault_location: str) -> dict:
        """Assess risks during fault and restoration."""
        return {
            "immediate_risks": [
                "Power surge to neighboring circuits",
                "Cascading failures if not quickly isolated",
                "Safety hazard to personnel"
            ],
            "restoration_risks": [
                "Inrush current damage if restored too quickly",
                "Secondary faults in parallel paths",
                "Feedback from renewable sources (if any)"
            ],
            "mitigation_recommended": [
                "Use synchronous generator for black-start if needed",
                "Coordinate with protective relays",
                "Staged load restoration"
            ]
        }
    
    def _generate_reasoning(self, analysis: dict) -> str:
        """Generate human-readable agent reasoning."""
        fault_loc = analysis["fault_location"]
        prop = analysis["propagation_trace"]
        iso = analysis["isolation_points"]
        impact = analysis["impact_assessment"]
        restore = analysis["restoration_estimate"]
        
        reasoning = f"""
        FAULT INTELLIGENCE ANALYSIS
        ============================
        
        SITUATION:
        Fault detected at component {fault_loc}.
        This affects {prop['total_affected']} components downstream:
        - {prop['feeders_affected']} feeders
        - {prop['buses_affected']} buses
        - {prop['transformers_affected']} transformers
        
        RECOMMENDED ISOLATION:
        Top priority: {iso[0]['component_id']} ({iso[0]['component_label']})
        Reason: {iso[0]['reason']}
        Will affect {iso[0]['affected_customers']} customers.
        
        IMPACT ASSESSMENT:
        Risk Level: {impact['cascading_risk']}
        Critical Infrastructure: {'YES - elevated concern' if impact['critical_infrastructure_affected'] else 'No'}
        
        RESTORATION STRATEGY:
        Fault Type: {restore['fault_type']}
        Estimated Time: {restore['estimated_time_minutes']} minutes
        Range: {restore['best_case_minutes']}-{restore['worst_case_minutes']} minutes
        
        RECOMMENDED STEPS:
        {chr(10).join(restore['restoration_steps'])}
        """
        
        return reasoning.strip()
