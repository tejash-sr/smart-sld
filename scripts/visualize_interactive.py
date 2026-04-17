#!/usr/bin/env python3
"""Generate interactive Digital Twin visualization of SLD topology."""

import json
import networkx as nx
from pathlib import Path
from typing import Dict, Any


def create_interactive_html(json_path: str, output_path: str = None) -> str:
    """
    Generate interactive HTML visualization using Plotly.
    Shows: topology graph with node properties, hover info, voltage levels, component types.
    
    Args:
        json_path: Path to extracted SLD JSON
        output_path: Optional output path (defaults to _interactive.html)
    
    Returns:
        Path to generated HTML file
    """
    
    with open(json_path) as f:
        data = json.load(f)
    
    # Create directed graph
    G = nx.DiGraph()
    
    # Component type colors and sizes
    node_colors = {}
    node_sizes = {}
    node_info = {}
    
    # Add sources (red, large)
    for source in data.get("sources", []):
        node_id = source["id"]
        G.add_node(node_id, label=source["name"], type="source", voltage=source.get("voltage", ""))
        node_colors[node_id] = "#FF6B6B"    # Red
        node_sizes[node_id] = 60
        node_info[node_id] = {
            "type": "Source (Incomer)",
            "voltage": source.get("voltage", "N/A"),
            "name": source["name"]
        }
    
    # Add transformers (yellow, large)
    for transformer in data.get("transformers", []):
        node_id = transformer["id"]
        G.add_node(node_id, label=transformer["name"], type="transformer",
                   hv_side=transformer.get("hv_side"), lv_side=transformer.get("lv_side"))
        node_colors[node_id] = "#FFD93D"    # Yellow
        node_sizes[node_id] = 50
        node_info[node_id] = {
            "type": "Transformer",
            "rating": transformer.get("rating", "N/A"),
            "hv_side": transformer.get("hv_side", "N/A"),
            "lv_side": transformer.get("lv_side", "N/A"),
            "name": transformer["name"]
        }
    
    # Add buses (green, medium)
    for bus in data.get("buses", []):
        node_id = bus["id"]
        G.add_node(node_id, label=bus["name"], type="bus", voltage=bus.get("voltage_level", ""))
        node_colors[node_id] = "#6BCB77"    # Green
        node_sizes[node_id] = 40
        node_info[node_id] = {
            "type": "Bus",
            "voltage": bus.get("voltage_level", "N/A"),
            "name": bus["name"]
        }
    
    # Add feeders (blue, small)
    for feeder in data.get("feeders", []):
        node_id = feeder["id"]
        G.add_node(node_id, label=feeder["name"], type="feeder", voltage=feeder.get("voltage", ""))
        node_colors[node_id] = "#4D96FF"    # Blue
        node_sizes[node_id] = 35
        node_info[node_id] = {
            "type": "Feeder (Distribution)",
            "voltage": feeder.get("voltage", "N/A"),
            "destination": feeder.get("destination", "N/A"),
            "name": feeder["name"]
        }
    
    # Add connections
    edge_traces = []
    for conn in data.get("connections", []):
        from_id = conn["from"]
        to_id = conn["to"]
        G.add_edge(from_id, to_id)
    
    # Use spring layout for better visualization
    pos = nx.spring_layout(G, k=2, iterations=50, seed=42)
    
    # Generate edge traces for Plotly
    edge_x = []
    edge_y = []
    for edge in G.edges():
        x0, y0 = pos[edge[0]]
        x1, y1 = pos[edge[1]]
        edge_x.extend([x0, x1, None])
        edge_y.extend([y0, y1, None])
    
    # Generate node traces
    node_x = [pos[node][0] for node in G.nodes()]
    node_y = [pos[node][1] for node in G.nodes()]
    node_color_list = [node_colors.get(node, "#CCCCCC") for node in G.nodes()]
    node_size_list = [node_sizes.get(node, 30) for node in G.nodes()]
    
    # Create hover text
    hover_text = []
    for node in G.nodes():
        info = node_info.get(node, {})
        hover_info = f"<b>{info.get('name', node)}</b><br>"
        hover_info += f"Type: {info.get('type', 'Unknown')}<br>"
        if "voltage" in info and info["voltage"]:
            hover_info += f"Voltage: {info['voltage']}<br>"
        if "rating" in info:
            hover_info += f"Rating: {info['rating']}<br>"
        if "hv_side" in info and info["hv_side"]:
            hover_info += f"HV: {info['hv_side']}, LV: {info['lv_side']}"
        hover_text.append(hover_info)
    
    # Build HTML with Plotly
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>SENTINEL - SLD Digital Twin Visualization</title>
        <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
        <style>
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                margin: 0;
                padding: 20px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
            }}
            .container {{
                max-width: 1400px;
                margin: 0 auto;
                background: white;
                border-radius: 10px;
                box-shadow: 0 10px 40px rgba(0,0,0,0.3);
                overflow: hidden;
            }}
            .header {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 30px;
                text-align: center;
            }}
            .header h1 {{
                margin: 0;
                font-size: 2.5em;
                font-weight: 300;
            }}
            .header p {{
                margin: 10px 0 0 0;
                opacity: 0.9;
            }}
            .controls {{
                padding: 20px;
                background: #f8f9fa;
                border-bottom: 1px solid #e0e0e0;
                display: flex;
                gap: 20px;
                align-items: center;
            }}
            .control-group {{
                flex: 1;
            }}
            .control-group label {{
                font-weight: bold;
                display: block;
                margin-bottom: 5px;
                color: #333;
            }}
            .legend {{
                display: flex;
                gap: 30px;
                flex-wrap: wrap;
            }}
            .legend-item {{
                display: flex;
                align-items: center;
                gap: 8px;
            }}
            .legend-box {{
                width: 20px;
                height: 20px;
                border-radius: 3px;
            }}
            #graph {{
                height: 700px;
                width: 100%;
            }}
            .stats {{
                padding: 20px;
                background: #f8f9fa;
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 15px;
                border-top: 1px solid #e0e0e0;
            }}
            .stat-box {{
                background: white;
                padding: 15px;
                border-radius: 5px;
                border-left: 4px solid #667eea;
            }}
            .stat-label {{
                font-size: 0.9em;
                color: #666;
                margin-bottom: 5px;
            }}
            .stat-value {{
                font-size: 1.8em;
                font-weight: bold;
                color: #333;
            }}
            .footer {{
                padding: 15px;
                background: #f8f9fa;
                text-align: center;
                font-size: 0.9em;
                color: #666;
                border-top: 1px solid #e0e0e0;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>⚡ SENTINEL Digital Twin</h1>
                <p>Interactive SLD Topology Visualization & Analysis</p>
            </div>
            
            <div class="controls">
                <div class="control-group">
                    <label>Legend (Component Types)</label>
                    <div class="legend">
                        <div class="legend-item">
                            <div class="legend-box" style="background: #FF6B6B;"></div>
                            <span>Sources (Incomers)</span>
                        </div>
                        <div class="legend-item">
                            <div class="legend-box" style="background: #FFD93D;"></div>
                            <span>Transformers</span>
                        </div>
                        <div class="legend-item">
                            <div class="legend-box" style="background: #6BCB77;"></div>
                            <span>Buses</span>
                        </div>
                        <div class="legend-item">
                            <div class="legend-box" style="background: #4D96FF;"></div>
                            <span>Feeders</span>
                        </div>
                    </div>
                </div>
            </div>
            
            <div id="graph"></div>
            
            <div class="stats">
                <div class="stat-box">
                    <div class="stat-label">Sources</div>
                    <div class="stat-value">{len(data.get("sources", []))}</div>
                </div>
                <div class="stat-box">
                    <div class="stat-label">Transformers</div>
                    <div class="stat-value">{len(data.get("transformers", []))}</div>
                </div>
                <div class="stat-box">
                    <div class="stat-label">Buses</div>
                    <div class="stat-value">{len(data.get("buses", []))}</div>
                </div>
                <div class="stat-box">
                    <div class="stat-label">Feeders</div>
                    <div class="stat-value">{len(data.get("feeders", []))}</div>
                </div>
                <div class="stat-box">
                    <div class="stat-label">Connections</div>
                    <div class="stat-value">{len(data.get("connections", []))}</div>
                </div>
                <div class="stat-box">
                    <div class="stat-label">Total Components</div>
                    <div class="stat-value">{len(G.nodes())}</div>
                </div>
            </div>
            
            <div class="footer">
                SENTINEL v0.2 | AI-Driven SLD Intelligence | Real-time Topology Analysis
            </div>
        </div>
        
        <script>
            var edge_trace = {{
                x: {json.dumps(edge_x)},
                y: {json.dumps(edge_y)},
                mode: 'lines',
                line: {{
                    width: 1.5,
                    color: '#999999'
                }},
                hoverinfo: 'none',
                showlegend: false
            }};

            var node_trace = {{
                x: {json.dumps(node_x)},
                y: {json.dumps(node_y)},
                mode: 'markers+text',
                text: {json.dumps([G.nodes[node].get("label", node) for node in G.nodes()])},
                textposition: 'top center',
                textfont: {{
                    size: 10,
                    color: '#333'
                }},
                hovertext: {json.dumps(hover_text)},
                hoverinfo: 'text',
                marker: {{
                    size: {json.dumps(node_size_list)},
                    color: {json.dumps(node_color_list)},
                    line: {{
                        width: 2,
                        color: '#fff'
                    }},
                    opacity: 0.9
                }},
                showlegend: false
            }};

            var data = [edge_trace, node_trace];
            
            var layout = {{
                title: '{{text: 'Substation Topology Graph (Interactive)', x: 0.5, xanchor: 'center'}}',
                showlegend: false,
                hovermode: 'closest',
                margin: {{
                    b: 20,
                    l: 5,
                    r: 5,
                    t: 40
                }},
                xaxis: {{
                    showgrid: false,
                    zeroline: false,
                    showticklabels: false
                }},
                yaxis: {{
                    showgrid: false,
                    zeroline: false,
                    showticklabels: false
                }},
                paper_bgcolor: '#f8f9fa',
                plot_bgcolor: '#f8f9fa'
            }};

            Plotly.newPlot('graph', data, layout, {{responsive: true}});
        </script>
    </body>
    </html>
    """
    
    # Save HTML
    if output_path is None:
        json_path_obj = Path(json_path)
        output_path = json_path_obj.parent / f"{json_path_obj.stem}_interactive.html"
    
    with open(output_path, "w") as f:
        f.write(html_content)
    
    print(f"✅ Interactive visualization saved: {output_path}")
    print(f"   Open in browser to explore topology interactively")
    
    return str(output_path)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python visualize_interactive.py <json_path> [output_path]")
        print("Example: python visualize_interactive.py data/real/katra_output.json")
        sys.exit(1)
    
    json_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    create_interactive_html(json_file, output_file)
