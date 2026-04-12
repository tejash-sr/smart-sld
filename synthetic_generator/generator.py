"""Generate synthetic SLD training data for model development.

Creates labeled SLD diagrams with known ground truth for training
and testing the CV pipeline without needing real utility diagrams.
"""

from __future__ import annotations

import json
import random
import uuid
from pathlib import Path

import numpy as np

# We'll generate SVG-based synthetic diagrams
# Actual rendering can be done with reportlab/cairo


# ─── Symbol Definitions ────────────────────────────────────────────────────────

SYMBOL_TEMPLATES = {
    "transformer_2w": {
        "width": 80,
        "height": 60,
        "has_labels": ["ICT-1", "ICT-2", "GT-1"],
        "voltage_options": [("220kV", "33kV"), ("132kV", "11kV"), ("400kV", "220kV")],
    },
    "circuit_breaker": {
        "width": 40,
        "height": 60,
        "labels": ["CB-101", "CB-102", "CB-201"],
    },
    "disconnect_switch": {
        "width": 40,
        "height": 60,
        "labels": ["DS-101", "DS-102", "DS-201"],
    },
    "busbar": {
        "width": 600,
        "height": 20,
        "labels": ["220kV BUSA", "33kV BUSB"],
    },
    "current_transformer": {
        "width": 30,
        "height": 50,
        "labels": ["CT-101", "CT-102", "CT-201"],
    },
    "voltage_transformer": {
        "width": 30,
        "height": 50,
        "labels": ["VT-101", "VT-102"],
    },
    "feeder_terminal": {
        "width": 40,
        "height": 40,
        "labels": ["F-BNG-220-101", "F-HYD-132-201", "FEEDER-1"],
    },
    "ground": {
        "width": 30,
        "height": 40,
        "labels": ["GND"],
    },
}


# ─── Layout Generator ──────────────────────────────────────────────────────────


class SyntheticSLDGenerator:
    """Generate synthetic Single Line Diagrams with known ground truth."""

    def __init__(self, seed: int | None = None):
        self.rng = random.Random(seed)
        self.diagrams = []

    def generate(self, n_diagrams: int = 50, output_dir: str = "data/synthetic"):
        """Generate n synthetic SLD diagrams."""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Store manifest of all generated diagrams with ground truth
        manifest = []

        for i in range(n_diagrams):
            diagram = self._generate_single(i)
            manifest.append(diagram["metadata"])

            # Render to image (placeholder - would need actual rendering)
            self._render_svg(diagram, output_path / f"sld_{i:04d}.svg")

        # Save ground truth
        with open(output_path / "manifest.json", "w") as f:
            json.dump(manifest, f, indent=2)

        return manifest

    def _generate_single(self, index: int) -> dict:
        """Generate a single synthetic SLD."""
        voltage_level = self.rng.choice(["220kV", "132kV", "33kV"])
        bus_count = self.rng.randint(1, 3)

        components = []
        connections = []

        # Generate busbars
        buses = []
        for b in range(bus_count):
            bus_id = f"BUS-{uuid.uuid4().hex[:8].upper()}"
            buses.append(
                {
                    "id": bus_id,
                    "label": f"{voltage_level} BUSB{chr(65+b)}",
                    "voltage": voltage_level,
                    "sections": [
                        {
                            "id": f"BUS-SEC-{uuid.uuid4().hex[:8].upper()}",
                            "from_x": 50 + b * 200,
                            "from_y": 100 + b * 150,
                            "to_x": 350 + b * 200,
                            "to_y": 100 + b * 150,
                        }
                    ],
                }
            )

        # Generate components for each bus
        component_id = 0
        for bus in buses:
            # Add transformer
            comp = {
                "id": f"COMP-{component_id:03d}",
                "type": "transformer_2w",
                "label": self.rng.choice(["ICT-1", "ICT-2", "GT-1"]),
                "voltage_primary": voltage_level,
                "voltage_secondary": self._lower_voltage(voltage_level),
                "rating": self.rng.choice(["100 MVA", "80 MVA", "50 MVA"]),
                "position": {
                    "x": bus["sections"][0]["from_x"] + 100,
                    "y": bus["sections"][0]["from_y"] + 80,
                },
                "confidence": 0.98,
            }
            components.append(comp)
            component_id += 1

            # Add breakers and feeders
            for j in range(self.rng.randint(2, 4)):
                # Circuit breaker
                cb = {
                    "id": f"COMP-{component_id:03d}",
                    "type": "circuit_breaker",
                    "label": f"CB-{100+j}",
                    "position": {
                        "x": bus["sections"][0]["from_x"] + 50 + j * 120,
                        "y": bus["sections"][0]["from_y"] - 40,
                    },
                    "confidence": 0.95,
                }
                components.append(cb)
                component_id += 1

                # CT after breaker
                ct = {
                    "id": f"COMP-{component_id:03d}",
                    "type": "current_transformer",
                    "label": f"CT-{100+j}",
                    "position": {
                        "x": cb["position"]["x"] + 50,
                        "y": bus["sections"][0]["from_y"] - 40,
                    },
                    "confidence": 0.94,
                }
                components.append(ct)
                component_id += 1

                # Feeder
                feeder = {
                    "id": f"COMP-{component_id:03d}",
                    "type": "feeder_terminal",
                    "label": f"F-{voltage_level.replace('kV','')}-{100+j}",
                    "position": {
                        "x": ct["position"]["x"] + 80,
                        "y": bus["sections"][0]["from_y"] - 40,
                    },
                    "confidence": 0.92,
                }
                components.append(feeder)
                component_id += 1

        diagram = {
            "diagram_id": f"SLD-SYN-{index:04d}",
            "extracted_at": "2024-01-01T00:00:00Z",
            "source_file": f"synthetic_sld_{index}.svg",
            "voltage_level": voltage_level,
            "confidence_summary": {
                "overall": 0.93,
                "symbol_detection": 0.96,
                "text_extraction": 0.89,
                "connectivity": 0.94,
            },
            "components": components,
            "buses": buses,
            "connections": connections,
            "metadata": {
                "is_synthetic": True,
                "generation_seed": index,
            },
        }

        self.diagrams.append(diagram)
        return diagram

    def _lower_voltage(self, v: str) -> str:
        mapping = {
            "400kV": "220kV",
            "220kV": "33kV",
            "132kV": "11kV",
            "66kV": "11kV",
            "33kV": "11kV",
            "11kV": "0.415kV",
        }
        return mapping.get(v, "11kV")

    def _render_svg(self, diagram: dict, output_path: Path):
        """Render diagram to SVG."""
        # SVG template
        width, height = 900, 700
        svg_lines = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">',
            f'<!-- Synthetic SLD: {diagram["diagram_id"]} -->',
            f'<rect width="{width}" height="{height}" fill="white"/>',
        ]

        # Render buses
        for bus in diagram.get("buses", []):
            for section in bus.get("sections", []):
                fx = section["from_x"]
                fy = section["from_y"]
                tx = section["to_x"]
                svg_lines.append(f'<line x1="{fx}" y1="{fy}" x2="{tx}" y2="{ty}" stroke="black" stroke-width="4"/>')

        # Render components
        for comp in diagram.get("components", []):
            x = comp["position"]["x"]
            y = comp["position"]["y"]
            ctype = comp["type"]

            if ctype == "transformer_2w":
                svg_lines.append(
                    f'<rect x="{x-40}" y="{y-30}" width="80" height="60" fill="none" stroke="black" stroke-width="2"/>'
                )
                svg_lines.append(f'<text x="{x}" y="{y+5}" text-anchor="middle" font-size="10">{comp["label"]}</text>')
            elif ctype == "circuit_breaker":
                svg_lines.append(
                    f'<rect x="{x-20}" y="{y-30}" width="40" height="60" fill="none" stroke="black" stroke-width="2"/>'
                )
                svg_lines.append(
                    f'<line x1="{x-15}" y1="{y-20}" x2="{x+15}" y2="{y+20}" stroke="black" stroke-width="2"/>'
                )
                svg_lines.append(f'<text x="{x}" y="{y+5}" text-anchor="middle" font-size="10">{comp["label"]}</text>')
            elif ctype == "disconnect_switch":
                svg_lines.append(
                    f'<rect x="{x-20}" y="{y-30}" width="40" height="60" fill="none" stroke="black" stroke-width="2"/>'
                )
                svg_lines.append(
                    f'<line x1="{x-10}" y1="{y-15}" x2="{x+10}" y2="{y+15}" stroke="black" stroke-width="2"/>'
                )
                svg_lines.append(f'<text x="{x}" y="{y+5}" text-anchor="middle" font-size="10">{comp["label"]}</text>')

        svg_lines.append("</svg>")

        with open(output_path, "w") as f:
            f.write("\n".join(svg_lines))


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate synthetic SLD training data")
    parser.add_argument("--n", type=int, default=50, help="Number of diagrams to generate")
    parser.add_argument("--output", type=str, default="data/synthetic", help="Output directory")
    args = parser.parse_args()

    gen = SyntheticSLDGenerator(seed=42)
    manifest = gen.generate(n_diagrams=args.n, output_dir=args.output)
    print(f"Generated {len(manifest)} synthetic SLDs in {args.output}/")