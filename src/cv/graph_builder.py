"""Graph construction from detected components and lines."""
from __future__ import annotations
import uuid
import networkx as nx
from src.models.sld_schema import (
    Component, ComponentType, Connection, ConnectionType,
    NetworkGraph, Bus, BusSection, Point, BoundingBox
)

class GraphBuilder:
    def __init__(self):
        self.graph = nx.Graph()
        self.component_map: dict[str, Component] = {}

    def add_component(self, component: Component) -> None:
        self.component_map[component.id] = component
        self.graph.add_node(component.id, **{
            "component_type": component.component_type.value,
            "voltage_level": component.voltage_level,
            "label": component.label,
            "position": component.position.model_dump() if component.position else None,
        })

    def add_connection(self, from_id: str, to_id: str,
                       connection_type: ConnectionType = ConnectionType.DIRECT,
                       metadata: dict | None = None) -> None:
        self.graph.add_edge(from_id, to_id,
                            connection_type=connection_type.value,
                            **(metadata or {}))

    def build(self) -> tuple[NetworkGraph, list[BusSection]]:
        bus_sections = self._detect_bus_sections()
        edge_list = [
            Connection(
                id=str(uuid.uuid4())[:8],
                from_component=u,
                to_component=v,
                connection_type=ConnectionType(e.get("connection_type", "direct")),
            )
            for u, v, e in self.graph.edges(data=True)
        ]
        buses = [
            Bus(id=str(uuid.uuid4())[:8],
                name=bs.label,
                voltage_level=bs.voltage or "unknown",
                component_ids=bs.component_ids)
            for bs in bus_sections
        ]
        return (NetworkGraph(nodes=list(self.component_map.values()),
                             edges=edge_list, buses=buses),
                bus_sections)

    def _detect_bus_sections(self) -> list[BusSection]:
        busbar_nodes = [
            n for n, d in self.graph.nodes(data=True)
            if d.get("component_type") == "busbar"
        ]
        visited: set[str] = set()
        bus_sections: list[BusSection] = []

        for bb in busbar_nodes:
            if bb in visited:
                continue
            cluster: set = set()
            self._flood_fill(bb, cluster, visited)
            if not cluster:
                continue
            voltages = [
                self.graph.nodes[n].get("voltage_level")
                for n in cluster if self.graph.nodes[n].get("voltage_level")
            ]
            voltage = voltages[0] if voltages else None
            label = f"BUS-{len(bus_sections) + 1}"
            if voltage:
                label += f" {voltage}"
            bus_sections.append(BusSection(
                id=str(uuid.uuid4())[:8],
                label=label,
                voltage=voltage,
                component_ids=list(cluster)
            ))

        if not bus_sections:
            bus_sections.append(BusSection(
                id=str(uuid.uuid4())[:8],
                label="DEFAULT",
                voltage=None,
                component_ids=list(self.graph.nodes)
            ))
        return bus_sections

    def _flood_fill(self, node: str, cluster: set, visited: set) -> None:
        visited.add(node)
        cluster.add(node)
        for neighbor in self.graph.neighbors(node):
            if neighbor not in visited:
                self._flood_fill(neighbor, cluster, visited)
