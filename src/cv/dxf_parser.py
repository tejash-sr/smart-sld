"""DXF/CAD parser for vector SLD input using ezdxf."""
from __future__ import annotations
import math
from dataclasses import dataclass, field
from ezdxf import readfile, readbytes
from ezdxf.document import Drawing
from ezdxf.enums import TextEntityAlignment
from src.models.sld_schema import Component, ComponentType, Point, BoundingBox

@dataclass
class DXFLine:
    start: tuple[float, float]
    end: tuple[float, float]
    layer: str
    line_type: str

@dataclass
class DXFComponent:
    component_type: str
    label: str
    layer: str
    insert_point: tuple[float, float]
    rotation: float = 0.0
    block_name: str | None = None
    bbox: BoundingBox | None = None

SYMBOL_MAP = {
    "TRANSFORMER": "transformer_2w", "XFMR": "transformer_2w", "XFMR2W": "transformer_2w",
    "ICT": "transformer_2w", "CB": "circuit_breaker", "BREAKER": "circuit_breaker",
    "DISC": "disconnect_switch", "DS": "disconnect_switch", "SWITCH": "disconnect_switch",
    "LBS": "load_break_switch", "LOADBREAK": "load_break_switch",
    "CT": "current_transformer", "VT": "voltage_transformer", "PT": "voltage_transformer",
    "BUS": "busbar", "BUSBAR": "busbar", "HVDC": "busbar",
    "GEN": "generator", "GENERATOR": "generator", "SYNC": "generator",
    "CAP": "capacitor", "CAPACITOR": "capacitor",
    "REACT": "reactor", "REACTOR": "reactor", "SHUNT": "reactor",
    "GND": "ground", "GROUND": "ground", "EARTH": "ground",
    "ARRESTER": "surge_arrester", "SA": "surge_arrester", "SPD": "surge_arrester",
    "FUSE": "fuse", "FUSE": "fuse",
    "FEEDER": "feeder_terminal", "TERM": "feeder_terminal", "TERMINAL": "feeder_terminal",
    "MOTOR": "motor", "MTR": "motor",
    "RELAY": "protection_relay", "PROT": "protection_relay",
}

WIRE_LAYERS = {"WIRES", "LINES", "CONNECTION", "CONN", "WIRE", "LINE", "0", "CONDUCTOR"}

LAYER_VOLTAGE_MAP = {
    "765KV": "765kV", "400KV": "400kV", "220KV": "220kV",
    "132KV": "132kV", "33KV": "33kV", "11KV": "11kV", "415V": "415V",
    "LV": "415V", "MV": "33kV", "HV": "220kV", "EHV": "400kV",
}

class DXFInterpreter:
    def __init__(self):
        self.components: list[DXFComponent] = []
        self.lines: list[DXFLine] = []
        self.text_labels: dict[tuple[float, float], str] = {}
        self.layer_voltage: dict[str, str] = {}

    def parse(self, dxf_path: str) -> tuple[list[DXFComponent], list[DXFLine]]:
        doc = readfile(dxf_path)
        msp = doc.modelspace()
        self._extract_all(msp, doc)
        return self.components, self.lines

    def parse_bytes(self, data: bytes) -> tuple[list[DXFComponent], list[DXFLine]]:
        doc = readbytes(data)
        msp = doc.modelspace()
        self._extract_all(msp, doc)
        return self.components, self.lines

    def _extract_all(self, msp, doc: Drawing):
        self._extract_blocks(doc)
        self._extract_inserts(msp)
        self._extract_lines(msp)
        self._extract_polylines(msp)
        self._extract_text(msp)
        self._extract_layer_props(doc)

    def _extract_blocks(self, doc: Drawing):
        pass

    def _extract_inserts(self, msp):
        for entity in msp.query("INSERT"):
            name = entity.dxf.name.upper()
            layer = entity.dxf.layer.upper()
            pt = entity.dxf.insert
            rotation = entity.dxf.rotation
            comp_type = self._map_name(name, layer)
            if not comp_type:
                continue
            label = self._find_nearest_text(pt, radius=80) or name
            voltage = self.layer_voltage.get(layer) or self._infer_voltage_from_label(label)
            bbox = self._get_block_bbox(doc, name) if name in doc.blocks else None
            self.components.append(DXFComponent(
                component_type=comp_type, label=label, layer=layer,
                insert_point=(pt.x, pt.y), rotation=rotation,
                block_name=name, bbox=bbox,
            ))

    def _extract_lines(self, msp):
        for entity in msp.query("LINE"):
            layer = entity.dxf.layer.upper()
            if layer in WIRE_LAYERS or layer == "0":
                self.lines.append(DXFLine(
                    start=(entity.dxf.start.x, entity.dxf.start.y),
                    end=(entity.dxf.end.x, entity.dxf.end.y),
                    layer=layer, line_type="LINE",
                ))

    def _extract_polylines(self, msp):
        for entity in msp.query("LWPOLYLINE"):
            layer = entity.dxf.layer.upper()
            if layer in WIRE_LAYERS or layer == "0":
                pts = list(entity.get_points())
                for i in range(len(pts) - 1):
                    self.lines.append(DXFLine(
                        start=(pts[i].x, pts[i].y), end=(pts[i+1].x, pts[i+1].y),
                        layer=layer, line_type="POLYLINE",
                    ))
        for entity in msp.query("POLYLINE"):
            layer = entity.dxf.layer.upper()
            if layer in WIRE_LAYERS or layer == "0":
                pts = [(v.dxf.location.x, v.dxf.location.y) for v in entity.vertices]
                for i in range(len(pts) - 1):
                    self.lines.append(DXFLine(
                        start=pts[i], end=pts[i+1],
                        layer=layer, line_type="POLYLINE",
                    ))

    def _extract_text(self, msp):
        for entity in msp.query("TEXT MTEXT"):
            layer = entity.dxf.layer.upper()
            if layer in {"SKIP", "ANNO", "DIMENSION", "DIM"}:
                continue
            try:
                pt = entity.dxf.insert
                text = getattr(entity, "text", None) or getattr(entity, "get_text", lambda: "")()
                if text:
                    self.text_labels[(round(pt.x, 1), round(pt.y, 1))] = str(text).strip()
            except Exception:
                pass

    def _extract_layer_props(self, doc: Drawing):
        try:
            layers = doc.layers
            for layer_name in layers:
                ln = layer_name.upper()
                for prefix, voltage in LAYER_VOLTAGE_MAP.items():
                    if prefix in ln:
                        self.layer_voltage[layer_name] = voltage
                        break
        except Exception:
            pass

    def _map_name(self, name: str, layer: str) -> str | None:
        combined = f"{name} {layer}"
        combined_upper = combined.upper()
        for keyword, ctype in SYMBOL_MAP.items():
            if keyword in combined_upper:
                return ctype
        return None

    def _find_nearest_text(self, point, radius: float = 80) -> str | None:
        best, best_dist = None, radius
        for (tx, ty), text in self.text_labels.items():
            dist = math.hypot(tx - point.x, ty - point.y)
            if dist < best_dist:
                best_dist = dist
                best = text
        return best

    def _get_block_bbox(self, doc: Drawing, block_name: str):
        try:
            block = doc.blocks.get(block_name)
            if not block:
                return None
            extents = block.extents
            if extents:
                return BoundingBox(
                    x_min=extents.min[0], y_min=extents.min[1],
                    x_max=extents.max[0], y_max=extents.max[1],
                )
        except Exception:
            pass
        return None

    def _infer_voltage_from_label(self, label: str) -> str | None:
        import re
        m = re.search(r'(\d+)\s*kV', label, re.IGNORECASE)
        if m:
            return f"{m.group(1)}kV"
        return None

    def to_components(self) -> list[Component]:
        return [
            Component(
                id=f"dxf_{i}_{c.insert_point[0]:.0f}_{c.insert_point[1]:.0f}",
                component_type=ComponentType(c.component_type)
                               if c.component_type in [e.value for e in ComponentType]
                               else ComponentType.UNKNOWN,
                label=c.label,
                voltage_level=self.layer_voltage.get(c.layer) or self._infer_voltage_from_label(c.label),
                position=Point(x=c.insert_point[0], y=c.insert_point[1]),
                bbox=c.bbox,
                confidence=0.95,
            )
            for i, c in enumerate(self.components)
        ]
