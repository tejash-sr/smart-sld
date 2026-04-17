#!/usr/bin/env python3
"""Anomaly & Fault Detection Layer — Rule-based diagnostic checks on extracted SLDs."""

import json
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime


class AnomalyDetector:
    """
    Detects anomalies and faults in extracted SLD topology:
    - Missing protection relays on feeders
    - Orphaned components (isolated nodes)
    - Voltage level violations
    - Transformer pairing inconsistencies
    - Unusual topology patterns
    """
    
    def __init__(self, extracted_json_path: str):
        """Initialize with extracted SLD JSON."""
        with open(extracted_json_path) as f:
            self.data = json.load(f)
        
        self.anomalies = []
        self.warnings = []
        self.recommendations = []
    
    def detect_all(self) -> Dict[str, Any]:
        """Run all anomaly detection checks."""
        self._check_orphaned_components()
        self._check_voltage_levels()
        self._check_protection_relays()
        self._check_transformer_pairing()
        self._check_feeder_balancing()
        
        return self.generate_report()
    
    def _check_orphaned_components(self):
        """Check for isolated/orphaned components not connected to network."""
        
        connected_ids = set()
        
        # Collect all component IDs mentioned in connections
        for conn in self.data.get("connections", []):
            connected_ids.add(conn.get("from"))
            connected_ids.add(conn.get("to"))
        
        all_component_ids = set()
        for comp_type in ["sources", "transformers", "buses", "feeders"]:
            for comp in self.data.get(comp_type, []):
                all_component_ids.add(comp.get("id"))
        
        orphaned = all_component_ids - connected_ids
        
        for comp_id in orphaned:
            self.anomalies.append({
                "severity": "HIGH",
                "type": "ORPHANED_COMPONENT",
                "component_id": comp_id,
                "message": f"Component {comp_id} is not connected to the network",
                "recommendation": f"Review {comp_id}: may be a spare/standby or topology error"
            })
    
    def _check_voltage_levels(self):
        """Check for voltage level inconsistencies."""
        
        # Define typical voltage levels in Indian substations
        standard_voltages = {"132kV", "66kV", "33kV", "11kV", "6.6kV", "0.4kV"}
        
        for source in self.data.get("sources", []):
            voltage = source.get("voltage", "").replace(" ", "")
            if voltage not in standard_voltages:
                self.warnings.append({
                    "severity": "MEDIUM",
                    "type": "NON_STANDARD_VOLTAGE",
                    "component_id": source.get("id"),
                    "voltage": voltage,
                    "message": f"Source {source.get('id')} has non-standard voltage: {voltage}",
                    "recommendation": f"Verify voltage specification; expected one of {standard_voltages}"
                })
        
        for bus in self.data.get("buses", []):
            voltage = bus.get("voltage_level", "").replace(" ", "")
            if voltage not in standard_voltages:
                self.warnings.append({
                    "severity": "LOW",
                    "type": "UNUSUAL_VOLTAGE",
                    "component_id": bus.get("id"),
                    "voltage": voltage,
                    "message": f"Bus {bus.get('id')} has unusual voltage: {voltage}",
                    "recommendation": f"May be valid; verify against SLD legend"
                })
    
    def _check_protection_relays(self):
        """Check for missing protection relays on feeders."""
        
        # Rule: Each feeder should have protection (relay/OCB)
        # This is a best-practice check; not all feeders may have explicit relay mention
        
        for feeder in self.data.get("feeders", []):
            feeder_id = feeder.get("id")
            feeder_name = feeder.get("name", "Unknown")
            
            # Check if feeder has "relay", "protection", "OCB" (Oil Circuit Breaker) in name
            has_protection = any(
                term in feeder_name.lower() 
                for term in ["relay", "protection", "ocb", "breaker", "trip", "fuse"]
            )
            
            if not has_protection:
                self.recommendations.append({
                    "severity": "MEDIUM",
                    "type": "MISSING_PROTECTION",
                    "component_id": feeder_id,
                    "feeder_name": feeder_name,
                    "message": f"Feeder {feeder_id} ({feeder_name}) may lack explicit protection relay marking",
                    "recommendation": "Verify protection scheme on SLD; all feeders require OC/EF protection"
                })
    
    def _check_transformer_pairing(self):
        """Check transformer pairing consistency."""
        
        transformers = self.data.get("transformers", [])
        
        # Check for HV/LV consistency
        for t1 in transformers:
            for t2 in transformers:
                if t1 == t2:
                    continue
                
                # If both transformers share same HV voltage, they should have similar LV
                if t1.get("hv_side") == t2.get("hv_side"):
                    if t1.get("lv_side") != t2.get("lv_side"):
                        self.warnings.append({
                            "severity": "LOW",
                            "type": "TRANSFORMER_MISMATCH",
                            "transformers": [t1.get("id"), t2.get("id")],
                            "message": f"Transformers {t1.get('id')} and {t2.get('id')} have same HV ({t1.get('hv_side')}) but different LV",
                            "recommendation": "May be intentional; verify design intent (voltage regulation, load balancing)"
                        })
    
    def _check_feeder_balancing(self):
        """Check for unusual feeder count or load distribution."""
        
        num_feeders = len(self.data.get("feeders", []))
        num_transformers = len(self.data.get("transformers", []))
        
        # Typical ratio: 3-6 feeders per transformer
        if num_transformers > 0:
            ratio = num_feeders / num_transformers
            
            if ratio < 2:
                self.warnings.append({
                    "severity": "LOW",
                    "type": "LOW_FEEDER_COUNT",
                    "count": num_feeders,
                    "transformers": num_transformers,
                    "message": f"Low feeder-to-transformer ratio: {ratio:.1f}:1 (typically 3-6)",
                    "recommendation": "Typical substations have 3-6 feeders per transformer; verify topology"
                })
            
            elif ratio > 8:
                self.warnings.append({
                    "severity": "MEDIUM",
                    "type": "HIGH_FEEDER_COUNT",
                    "count": num_feeders,
                    "transformers": num_transformers,
                    "message": f"High feeder-to-transformer ratio: {ratio:.1f}:1 (typically 3-6)",
                    "recommendation": "May indicate hub substation or tap-off poles; high maintenance complexity"
                })
    
    def generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive anomaly report."""
        
        return {
            "report_timestamp": datetime.now().isoformat(),
            "diagnosis": {
                "critical_anomalies": [a for a in self.anomalies if a["severity"] == "HIGH"],
                "warnings": [w for w in self.warnings],
                "recommendations": [r for r in self.recommendations]
            },
            "summary": {
                "total_issues": len(self.anomalies) + len(self.warnings),
                "critical_count": len([a for a in self.anomalies if a["severity"] == "HIGH"]),
                "warning_count": len(self.warnings),
                "recommendation_count": len(self.recommendations),
                "system_health": self._calculate_health_score()
            },
            "topology_metrics": {
                "sources": len(self.data.get("sources", [])),
                "transformers": len(self.data.get("transformers", [])),
                "buses": len(self.data.get("buses", [])),
                "feeders": len(self.data.get("feeders", [])),
                "connections": len(self.data.get("connections", []))
            }
        }
    
    def _calculate_health_score(self) -> str:
        """Calculate overall system health score (0-100)."""
        
        total_issues = len(self.anomalies) + len(self.warnings)
        critical_severity = len([a for a in self.anomalies if a["severity"] == "HIGH"]) * 30
        
        score = max(0, 100 - total_issues * 5 - critical_severity)
        
        if score >= 90:
            return f"{score}/100 — ✅ HEALTHY (Production Ready)"
        elif score >= 70:
            return f"{score}/100 — ⚠️  ACCEPTABLE (Review Recommended)"
        else:
            return f"{score}/100 — 🔴 CRITICAL (Requires Investigation)"


def run_diagnostics(json_path: str, output_path: str = None) -> Dict[str, Any]:
    """
    Run full diagnostic on extracted SLD.
    
    Args:
        json_path: Path to extracted JSON
        output_path: Optional output path for report
    
    Returns:
        Diagnostic report dict
    """
    
    detector = AnomalyDetector(json_path)
    report = detector.detect_all()
    
    # Save report if output path provided
    if output_path is None:
        json_path_obj = Path(json_path)
        output_path = json_path_obj.parent / f"{json_path_obj.stem}_diagnostics.json"
    
    with open(output_path, "w") as f:
        json.dump(report, f, indent=2)
    
    print(f"\n{'='*60}")
    print(f"🔍 SENTINEL Diagnostic Report")
    print(f"{'='*60}\n")
    
    print(f"📊 Topology Metrics:")
    for key, value in report["topology_metrics"].items():
        print(f"   {key.capitalize()}: {value}")
    
    print(f"\n⚠️  System Health: {report['summary']['system_health']}")
    
    if report["diagnosis"]["critical_anomalies"]:
        print(f"\n🔴 CRITICAL ANOMALIES ({len(report['diagnosis']['critical_anomalies'])}):")
        for anomaly in report["diagnosis"]["critical_anomalies"]:
            print(f"   • {anomaly['message']}")
            print(f"     → {anomaly['recommendation']}")
    
    if report["diagnosis"]["warnings"]:
        print(f"\n⚠️  Warnings ({len(report['diagnosis']['warnings'])}):")
        for warning in report["diagnosis"]["warnings"]:
            print(f"   • {warning['message']}")
    
    if report["diagnosis"]["recommendations"]:
        print(f"\n💡 Recommendations ({len(report['diagnosis']['recommendations'])}):")
        for rec in report["diagnosis"]["recommendations"][:3]:  # Show top 3
            print(f"   • {rec['message']}")
    
    print(f"\n✅ Report saved: {output_path}\n")
    
    return report


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python anomaly_detector.py <json_path> [output_path]")
        print("Example: python anomaly_detector.py data/real/katra_output.json")
        sys.exit(1)
    
    json_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    run_diagnostics(json_file, output_file)
