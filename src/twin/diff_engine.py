"""SLD Diff Engine - Compare two topologies and detect changes."""
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Optional
import json
from datetime import datetime


@dataclass
class ComponentDiff:
    """Represents a change in a component."""
    change_type: str  # "added", "removed", "modified"
    component_id: str
    component_type: str
    component_label: str
    old_state: dict | None = None
    new_state: dict | None = None
    timestamp: str = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow().isoformat()


@dataclass
class ConnectionDiff:
    """Represents a change in a connection."""
    change_type: str  # "added", "removed", "modified"
    from_id: str
    to_id: str
    from_label: str
    to_label: str
    old_type: Optional[str] = None
    new_type: Optional[str] = None
    timestamp: str = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow().isoformat()


@dataclass
class TopologyDiff:
    """Complete diff between two topologies."""
    old_batch_id: str
    new_batch_id: str
    timestamp: str
    
    component_diffs: list[ComponentDiff]
    connection_diffs: list[ConnectionDiff]
    
    # Statistics
    components_added: int = 0
    components_removed: int = 0
    components_modified: int = 0
    connections_added: int = 0
    connections_removed: int = 0
    
    # Risk assessment
    critical_changes: list[str] = None
    
    def __post_init__(self):
        if self.critical_changes is None:
            self.critical_changes = []
        
        # Calculate statistics
        self.components_added = sum(1 for d in self.component_diffs if d.change_type == "added")
        self.components_removed = sum(1 for d in self.component_diffs if d.change_type == "removed")
        self.components_modified = sum(1 for d in self.component_diffs if d.change_type == "modified")
        self.connections_added = sum(1 for d in self.connection_diffs if d.change_type == "added")
        self.connections_removed = sum(1 for d in self.connection_diffs if d.change_type == "removed")
    
    def to_dict(self) -> dict:
        """Convert to dict for JSON serialization."""
        return {
            "old_batch_id": self.old_batch_id,
            "new_batch_id": self.new_batch_id,
            "timestamp": self.timestamp,
            "component_diffs": [asdict(d) for d in self.component_diffs],
            "connection_diffs": [asdict(d) for d in self.connection_diffs],
            "statistics": {
                "components_added": self.components_added,
                "components_removed": self.components_removed,
                "components_modified": self.components_modified,
                "connections_added": self.connections_added,
                "connections_removed": self.connections_removed,
            },
            "critical_changes": self.critical_changes
        }


class SLDDiffEngine:
    """Compare two ExtractedSLD objects and produce a diff."""
    
    def compare(self, old_sld: dict, new_sld: dict) -> TopologyDiff:
        """
        Compare two SLD extractions and return differences.
        
        Args:
            old_sld: First ExtractedSLD dict
            new_sld: Second ExtractedSLD dict
            
        Returns:
            TopologyDiff object with all changes
        """
        old_comps = {c["id"]: c for c in old_sld.get("components", [])}
        new_comps = {c["id"]: c for c in new_sld.get("components", [])}
        
        old_conns_set = self._connection_set(old_sld.get("connections", []))
        new_conns_set = self._connection_set(new_sld.get("connections", []))
        
        # Component diffs
        component_diffs = []
        
        # Added components
        for comp_id, new_comp in new_comps.items():
            if comp_id not in old_comps:
                component_diffs.append(ComponentDiff(
                    change_type="added",
                    component_id=comp_id,
                    component_type=new_comp.get("component_type"),
                    component_label=new_comp.get("label", ""),
                    new_state=new_comp
                ))
        
        # Removed components
        for comp_id, old_comp in old_comps.items():
            if comp_id not in new_comps:
                component_diffs.append(ComponentDiff(
                    change_type="removed",
                    component_id=comp_id,
                    component_type=old_comp.get("component_type"),
                    component_label=old_comp.get("label", ""),
                    old_state=old_comp
                ))
        
        # Modified components
        for comp_id in old_comps.keys() & new_comps.keys():
            old_comp = old_comps[comp_id]
            new_comp = new_comps[comp_id]
            
            # Check if any critical properties changed
            critical_fields = ["voltage_level", "component_type", "position"]
            changed = False
            
            for field in critical_fields:
                if old_comp.get(field) != new_comp.get(field):
                    changed = True
                    break
            
            if changed:
                component_diffs.append(ComponentDiff(
                    change_type="modified",
                    component_id=comp_id,
                    component_type=new_comp.get("component_type"),
                    component_label=new_comp.get("label", ""),
                    old_state=old_comp,
                    new_state=new_comp
                ))
        
        # Connection diffs
        connection_diffs = []
        
        # Added connections
        for new_conn in new_conns_set:
            if new_conn not in old_conns_set:
                conn_dict = new_sld.get("connections", [])
                conn_match = next((c for c in conn_dict 
                                 if c["from_component"] == new_conn[0] 
                                 and c["to_component"] == new_conn[1]), None)
                
                if conn_match:
                    connection_diffs.append(ConnectionDiff(
                        change_type="added",
                        from_id=new_conn[0],
                        to_id=new_conn[1],
                        from_label=self._get_label(new_conn[0], new_comps),
                        to_label=self._get_label(new_conn[1], new_comps),
                        new_type=conn_match.get("connection_type")
                    ))
        
        # Removed connections
        for old_conn in old_conns_set:
            if old_conn not in new_conns_set:
                conn_dict = old_sld.get("connections", [])
                conn_match = next((c for c in conn_dict 
                                 if c["from_component"] == old_conn[0] 
                                 and c["to_component"] == old_conn[1]), None)
                
                if conn_match:
                    connection_diffs.append(ConnectionDiff(
                        change_type="removed",
                        from_id=old_conn[0],
                        to_id=old_conn[1],
                        from_label=self._get_label(old_conn[0], old_comps),
                        to_label=self._get_label(old_conn[1], old_comps),
                        old_type=conn_match.get("connection_type")
                    ))
        
        # Assess critical changes
        critical_changes = self._assess_criticality(
            component_diffs, connection_diffs, old_sld, new_sld
        )
        
        diff = TopologyDiff(
            old_batch_id=old_sld.get("_batch_id", "unknown"),
            new_batch_id=new_sld.get("_batch_id", "unknown"),
            timestamp=datetime.utcnow().isoformat(),
            component_diffs=component_diffs,
            connection_diffs=connection_diffs,
            critical_changes=critical_changes
        )
        
        return diff
    
    def _connection_set(self, connections: list) -> set:
        """Convert connections to a set of tuples for comparison."""
        return {(c["from_component"], c["to_component"]) for c in connections}
    
    def _get_label(self, comp_id: str, comps_dict: dict) -> str:
        """Get component label by ID."""
        return comps_dict.get(comp_id, {}).get("label", comp_id)
    
    def _assess_criticality(self, comp_diffs, conn_diffs, old_sld, new_sld) -> list[str]:
        """Assess which changes are critical for grid operations."""
        critical = []
        
        # Critical: Bus-level changes
        old_buses = old_sld.get("buses", [])
        new_buses = new_sld.get("buses", [])
        
        if len(old_buses) != len(new_buses):
            critical.append(
                f"Bus count changed: {len(old_buses)} → {len(new_buses)}"
            )
        
        # Critical: Feeder removal
        for diff in comp_diffs:
            if diff.change_type == "removed" and "feeder" in diff.component_type.lower():
                critical.append(
                    f"Feeder removed: {diff.component_label}"
                )
        
        # Critical: High connectivity losses
        removed_connections = sum(1 for d in conn_diffs if d.change_type == "removed")
        if removed_connections > 5:
            critical.append(
                f"Many connections removed: {removed_connections} connections lost"
            )
        
        # Critical: Voltage level changes
        for diff in comp_diffs:
            if diff.change_type == "modified":
                old_v = diff.old_state.get("voltage_level")
                new_v = diff.new_state.get("voltage_level")
                if old_v != new_v:
                    critical.append(
                        f"Voltage changed on {diff.component_label}: {old_v} → {new_v}"
                    )
        
        return critical
