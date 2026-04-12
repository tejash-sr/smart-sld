"""GraphML export for network analysis tools (NetworkX, yEd, etc.)."""
from __future__ import annotations
from pathlib import Path
import networkx as nx
from src.models.sld_schema import ExtractedSLD, Component, Connection

def sld_to_networkx(sld: ExtractedSLD) -> nx.Graph:
    G = nx.Graph()
    for comp in sld.components:
        G.add_node(comp.id,
                   label=comp.label or "",
                   component_type=comp.component_type.value,
                   voltage_level=comp.voltage_level or "",
                   confidence=comp.confidence,
                   position_x=comp.position.x, position_y=comp.position.y)
    for conn in sld.connections:
        G.add_edge(conn.from_component, conn.to_component,
                   connection_type=conn.connection_type.value,
                   label=conn.label or "",
                   id=conn.id)
    return G

def export_to_graphml(sld: ExtractedSLD, output_path: str | Path) -> Path:
    """Export ExtractedSLD to GraphML for use in yEd, Gephi, NetworkX."""
    G = sld_to_networkx(sld)
    path = Path(output_path)
    nx.write_graphml(G, str(path))
    return path

def export_to_csv(sld: ExtractedSLD, output_dir: str | Path) -> dict[Path]:
    """Export components and connections to CSV files."""
    import csv
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    comp_path = out_dir / "components.csv"
    with open(comp_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["id","component_type","label","voltage_level","x","y","confidence"])
        w.writeheader()
        for c in sld.components:
            w.writerow({
                "id": c.id, "component_type": c.component_type.value,
                "label": c.label or "", "voltage_level": c.voltage_level or "",
                "x": c.position.x, "y": c.position.y,
                "confidence": c.confidence,
            })

    conn_path = out_dir / "connections.csv"
    with open(conn_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["id","from_component","to_component","type","label"])
        w.writeheader()
        for c in sld.connections:
            w.writerow({
                "id": c.id, "from_component": c.from_component,
                "to_component": c.to_component,
                "type": c.connection_type.value, "label": c.label or "",
            })

    return {"components": comp_path, "connections": conn_path}
