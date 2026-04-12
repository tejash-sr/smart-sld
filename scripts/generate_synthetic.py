#!/usr/bin/env python3
"""Generate synthetic SLD training data with ground truth + rendered PNG images."""
import json, math, random, uuid, argparse
from pathlib import Path
from PIL import Image, ImageDraw

COMPONENT_TYPES = [
    "transformer_2w", "circuit_breaker", "disconnect_switch", "busbar",
    "current_transformer", "voltage_transformer", "reactor", "capacitor",
    "feeder_terminal", "ground", "surge_arrester", "fuse",
    "load_break_switch", "transformer_3w", "generator",
]
VOLTAGE_LEVELS = ["765kV", "400kV", "220kV", "132kV", "33kV", "11kV", "415V"]
IMG_W, IMG_H = 1200, 800

SYMBOL_COLORS = {
    "transformer_2w": (245, 158, 11), "transformer_3w": (249, 115, 22),
    "busbar": (59, 130, 246), "circuit_breaker": (34, 197, 94),
    "disconnect_switch": (6, 182, 212), "load_break_switch": (139, 92, 246),
    "current_transformer": (236, 72, 153), "voltage_transformer": (217, 70, 239),
    "reactor": (132, 204, 22), "capacitor": (163, 230, 53),
    "generator": (239, 68, 68), "feeder_terminal": (100, 116, 139),
    "ground": (107, 114, 128), "surge_arrester": (244, 63, 94),
    "fuse": (168, 85, 247), "unknown": (71, 85, 105),
}

def draw_symbol(draw, ctype: str, x: int, y: int, color: tuple):
    """Draw a symbol at (x,y) center on the ImageDraw context."""
    if ctype == "busbar":
        draw.rectangle([x - 60, y - 6, x + 60, y + 6], fill=color, outline=(0, 0, 0), width=2)
    elif ctype.startswith("transformer"):
        draw.ellipse([x - 14, y - 14, x + 14, y + 14], fill=color, outline=(0, 0, 0), width=2)
    elif ctype == "circuit_breaker":
        draw.rectangle([x - 11, y - 11, x + 11, y + 11], fill=color, outline=(0, 0, 0), width=2)
        draw.line([x - 7, y - 7, x + 7, y + 7], fill=(0, 0, 0), width=2)
        draw.line([x + 7, y - 7, x - 7, y + 7], fill=(0, 0, 0), width=2)
    elif ctype == "disconnect_switch" or ctype == "load_break_switch":
        draw.rectangle([x - 9, y - 9, x + 9, y + 9], fill=color, outline=(0, 0, 0), width=2)
        draw.line([x - 6, y - 6, x + 6, y + 6], fill=(0, 0, 0), width=1)
    elif ctype == "current_transformer" or ctype == "voltage_transformer":
        draw.ellipse([x - 10, y - 10, x + 10, y + 10], fill=color, outline=(0, 0, 0), width=2)
    elif ctype == "capacitor":
        draw.rectangle([x - 8, y - 14, x + 8, y + 14], fill=color, outline=(0, 0, 0), width=2)
    elif ctype == "ground":
        draw.line([x, y - 8, x, y + 4], fill=color, width=2)
        draw.line([x - 10, y + 4, x + 10, y + 4], fill=color, width=2)
        draw.line([x - 7, y + 7, x + 7, y + 7], fill=color, width=2)
        draw.line([x - 4, y + 10, x + 4, y + 10], fill=color, width=2)
    elif ctype == "reactor":
        draw.ellipse([x - 13, y - 13, x + 13, y + 13], fill=color, outline=(0, 0, 0), width=2)
        draw.ellipse([x - 7, y - 7, x + 7, y + 7], fill=(255, 255, 255), outline=(0, 0, 0), width=1)
    elif ctype == "surge_arrester":
        draw.ellipse([x - 9, y - 9, x + 9, y + 9], fill=color, outline=(0, 0, 0), width=2)
        draw.ellipse([x - 4, y - 4, x + 4, y + 4], fill=(255, 255, 255), outline=(0, 0, 0), width=1)
    elif ctype == "fuse":
        draw.rectangle([x - 7, y - 7, x + 7, y + 7], fill=color, outline=(0, 0, 0), width=2)
        draw.line([x - 5, y, x + 5, y], fill=(0, 0, 0), width=2)
    elif ctype == "feeder_terminal":
        draw.ellipse([x - 8, y - 8, x + 8, y + 8], fill=color, outline=(0, 0, 0), width=2)
    else:
        draw.ellipse([x - 9, y - 9, x + 9, y + 9], fill=color, outline=(0, 0, 0), width=2)


def generate_sld(seed: int, n_components: int = 25) -> tuple[dict, Image.Image]:
    rng = random.Random(seed)
    voltage = rng.choice(VOLTAGE_LEVELS)
    n_bus_sections = rng.randint(1, 2)

    components, connections = [], []
    busbar_y = IMG_H // 2
    used_positions = []

    def snap(v, grid=40):
        return round(v / grid) * grid

    def is_free(x, y, radius=55):
        return all(math.hypot(px - x, py - y) >= radius for px, py in used_positions)

    def free_pos():
        for _ in range(300):
            x, y = snap(rng.randint(80, IMG_W - 80)), snap(rng.randint(60, IMG_H - 60))
            if is_free(x, y):
                used_positions.append((x, y))
                return x, y
        return snap(rng.randint(80, IMG_W - 80)), snap(rng.randint(60, IMG_H - 60))

    # Busbars
    busbar_ids = []
    for bi in range(n_bus_sections):
        bx = IMG_W // (n_bus_sections + 1) * (bi + 1)
        by = busbar_y + (bi - n_bus_sections // 2) * 80
        bid = f"bus_{bi}"
        busbar_ids.append(bid)
        used_positions.append((bx, by))
        components.append({
            "id": bid, "component_type": "busbar",
            "label": f"BUS-{bi+1}", "voltage_level": voltage,
            "position": {"x": float(bx), "y": float(by)},
            "bbox": {"x_min": float(bx-60), "y_min": float(by-6), "x_max": float(bx+60), "y_max": float(by+6)},
            "confidence": 0.99,
        })

    # Components
    feeder_count = 0
    for _ in range(n_components):
        ctype = rng.choice([c for c in COMPONENT_TYPES if c != "busbar"])
        x, y = free_pos()
        while abs(y - busbar_y) < 50:
            y = snap(rng.randint(60, IMG_H - 60))

        cid = f"comp_{uuid.uuid4().hex[:6]}"
        label = None
        if ctype == "feeder_terminal":
            feeder_count += 1
            label = f"F{feeder_count}"
        elif ctype == "transformer_2w":
            label = f"T{feeder_count}"
        elif ctype == "generator":
            label = f"G{feeder_count}"
        elif ctype == "ground":
            label = "GND"

        components.append({
            "id": cid, "component_type": ctype, "label": label,
            "voltage_level": voltage,
            "position": {"x": float(x), "y": float(y)},
            "bbox": {"x_min": float(x-15), "y_min": float(y-15), "x_max": float(x+15), "y_max": float(y+15)},
            "confidence": round(rng.uniform(0.85, 0.98), 3),
        })

        # Connect to nearest busbar
        nearest_bus = min(busbar_ids, key=lambda b: math.hypot(
            next(c["position"]["x"] for c in components if c["id"] == b) - x,
            next(c["position"]["y"] for c in components if c["id"] == b) - y
        ))
        connections.append({
            "id": f"conn_{uuid.uuid4().hex[:6]}",
            "from_component": cid, "to_component": nearest_bus,
            "connection_type": "ac_line",
            "intermediate_points": [{"x": float(x), "y": float(busbar_y + (components[[c["id"] for c in components].index(nearest_bus)]["position"]["y"] - busbar_y) // 2 if nearest_bus in [c["id"] for c in components] else float(y))}],
        })

    # Inter-busbar connections
    for i in range(len(busbar_ids) - 1):
        connections.append({
            "id": f"conn_{uuid.uuid4().hex[:6]}",
            "from_component": busbar_ids[i], "to_component": busbar_ids[i+1],
            "connection_type": "ac_line", "intermediate_points": [],
        })

    gt = {
        "version": "1.0", "generator": "sld_interpreter",
        "voltage_levels": [voltage],
        "components": components, "connections": connections,
        "metadata": {"seed": seed, "n_components": n_components},
    }

    # Render image
    img = Image.new("RGB", (IMG_W, IMG_H), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)

    # Draw connections
    comp_by_id = {c["id"]: c for c in components}
    for conn in connections:
        fc = comp_by_id.get(conn["from_component"])
        tc = comp_by_id.get(conn["to_component"])
        if fc and tc:
            fx, fy = int(fc["position"]["x"]), int(fc["position"]["y"])
            tx, ty = int(tc["position"]["x"]), int(tc["position"]["y"])
            draw.line([(fx, fy), (tx, ty)], fill=(60, 60, 60), width=2)
            for pt in conn.get("intermediate_points", []):
                draw.ellipse([int(pt["x"])-3, int(pt["y"])-3, int(pt["x"])+3, int(pt["y"])+3], fill=(60, 60, 60))

    # Draw components
    for comp in components:
        x, y = int(comp["position"]["x"]), int(comp["position"]["y"])
        color = SYMBOL_COLORS.get(comp["component_type"], SYMBOL_COLORS["unknown"])
        draw_symbol(draw, comp["component_type"], x, y, color)
        if comp.get("label"):
            draw.text((x + 14, y - 7), str(comp["label"]), fill=(0, 0, 0))
        if comp.get("voltage_level"):
            draw.text((x + 14, y + 3), comp["voltage_level"], fill=(50, 50, 180))

    return gt, img


def generate_dataset(output_dir: Path, n_samples: int, start_seed: int = 0,
                     render_images: bool = True):
    output_dir.mkdir(parents=True, exist_ok=True)
    for i in range(start_seed, start_seed + n_samples):
        n_comp = random.randint(18, 35)
        gt, img = generate_sld(i, n_components=n_comp)
        stem = f"sld_{i:03d}"

        gt_path = output_dir / f"{stem}_gt.json"
        with open(gt_path, "w") as f:
            json.dump(gt, f, indent=2)

        if render_images:
            img_path = output_dir / f"{stem}.png"
            img.save(img_path, "PNG")

        print(f"  {stem}: {len(gt['components'])} components, {len(gt['connections'])} connections")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", default="data/synthetic")
    ap.add_argument("--n", type=int, default=50)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--no-images", action="store_true")
    args = ap.parse_args()
    print(f"Generating {args.n} synthetic SLDs in {args.output}")
    generate_dataset(Path(args.output), args.n, start_seed=args.seed,
                    render_images=not args.no_images)
    print("Done.")
