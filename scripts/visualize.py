#!/usr/bin/env python3
"""Generate network graph visualization from extracted SLD JSON."""

import json
import networkx as nx
import matplotlib.pyplot as plt
from pathlib import Path

# Load KATRA extraction
json_path = Path("data/real/katra_output.json")
with open(json_path) as f:
    data = json.load(f)

# Create directed graph
G = nx.DiGraph()

# Add nodes with labels and types
node_colors = {}
for source in data.get("sources", []):
    G.add_node(source["id"], label=source["name"], type="source")
    node_colors[source["id"]] = "#FF6B6B"

for transformer in data.get("transformers", []):
    G.add_node(transformer["id"], label=transformer["name"], type="transformer")
    node_colors[transformer["id"]] = "#FFD93D"

for bus in data.get("buses", []):
    G.add_node(bus["id"], label=bus["name"], type="bus")
    node_colors[bus["id"]] = "#6BCB77"

for feeder in data.get("feeders", []):
    G.add_node(feeder["id"], label=feeder["name"], type="feeder")
    node_colors[feeder["id"]] = "#4D96FF"

# Add connections
for conn in data.get("connections", []):
    G.add_edge(conn["from"], conn["to"])

# Layout
pos = nx.spring_layout(G, k=3, iterations=50, seed=42)

# Visualization
fig, ax = plt.subplots(figsize=(16, 12), dpi=100)

# Draw network
colors = [node_colors.get(node, "#CCCCCC") for node in G.nodes()]
nx.draw_networkx_nodes(G, pos, node_color=colors, node_size=800, ax=ax, alpha=0.8)
nx.draw_networkx_edges(G, pos, edge_color="#999999", arrows=True, arrowsize=20, 
                       connectionstyle="arc3,rad=0.1", ax=ax, alpha=0.6, width=1.5)

# Labels
labels = {node: G.nodes[node].get("label", node) for node in G.nodes()}
nx.draw_networkx_labels(G, pos, labels, font_size=8, font_weight="bold", ax=ax)

# Legend
from matplotlib.patches import Patch
legend_elements = [
    Patch(facecolor="#FF6B6B", label="Sources (Incomers)"),
    Patch(facecolor="#FFD93D", label="Transformers"),
    Patch(facecolor="#6BCB77", label="Buses"),
    Patch(facecolor="#4D96FF", label="Feeders")
]
ax.legend(handles=legend_elements, loc="upper left", fontsize=10)

ax.set_title("KATRA 132/33 KV GSS - Network Topology", fontsize=16, fontweight="bold")
ax.axis("off")

# Save
output_path = Path("data/real/katra_graph.png")
plt.tight_layout()
plt.savefig(output_path, dpi=150, bbox_inches="tight", facecolor="white")
print(f"✅ Visualization saved: {output_path}")

# Stats
print(f"\n📊 Network Statistics:")
print(f"   Nodes: {G.number_of_nodes()}")
print(f"   Edges: {G.number_of_edges()}")
print(f"   Sources: {len(data['sources'])}")
print(f"   Transformers: {len(data['transformers'])}")
print(f"   Buses: {len(data['buses'])}")
print(f"   Feeders: {len(data['feeders'])}")
print(f"   Connections: {len(data['connections'])}")
