"""IEC 61850 SCL exporter - converts ExtractedSLD to SCL XML for SCADA integration."""
from __future__ import annotations
import uuid, io
from pathlib import Path
from lxml import etree as ET
from src.models.sld_schema import ExtractedSLD, Component

LN_TYPE_MAP = {
    "circuit_breaker": "XCBR", "disconnect_switch": "DSIS",
    "load_break_switch": "DCSW", "current_transformer": "TCTR",
    "voltage_transformer": "TVTR", "transformer_2w": "PDIF",
    "transformer_3w": "PDIF", "ground": "FSCH",
    "reactor": "SRER", "capacitor": "CACL",
    "generator": "GEN", "feeder_terminal": "XCBR",
}

class SCLExporter:
    NS = "http://www.iec-61850.com/2007/SCL"

    def __init__(self, ied_name: str = "PROT_01", desc: str = "SLD-derived"):
        self.ied_name = ied_name
        self.desc = desc
        self._added_ln_types: set = set()

    def export(self, sld: ExtractedSLD, output_path: str | Path) -> Path:
        root = ET.Element("SCL", nsmap={"scl": self.NS})
        ET.SubElement(root, "Header", id=str(uuid.uuid4())[:8],
                      version="1.0", revision="2007B", toolID="SLD Interpreter v0.1")
        sub = self._build_substation(root, sld)
        root.append(sub)
        tree = ET.ElementTree(root)
        path = Path(output_path)
        tree.write(str(path), xml_declaration=True, encoding="UTF-8", pretty_print=True)
        return path

    def _build_substation(self, root: ET.Element, sld: ExtractedSLD) -> ET.Element:
        name = (sld.source_filename or "SUBSTATION").replace(".png","").replace(".pdf","")
        sub = ET.SubElement(root, "Substation", name=name)
        for bus in (sld.buses or []):
            vl_name = bus.name.replace(" ", "_")
            vl = ET.SubElement(sub, "VoltageLevel", name=vl_name)
            if bus.voltage_level:
                vl.set("voltage", bus.voltage_level)
            for comp_id in bus.component_ids:
                comps = [c for c in sld.components if c.id == comp_id]
                if not comps:
                    continue
                comp = comps[0]
                self._add_functional_container(vl, comp, sld)
        return sub

    def _add_functional_container(self, parent: ET.Element, comp: Component, sld: ExtractedSLD) -> None:
        fn = ET.SubElement(parent, "Function", name=comp.label or comp.id)
        eq_type = self._comp_to_eq_type(comp.component_type.value)
        ET.SubElement(fn, "GeneralEquipment",
                      name=comp.label or f"EQ_{comp.id[:6]}",
                      type=eq_type)
        ln_class = LN_TYPE_MAP.get(comp.component_type.value, "SARC")
        ln_type = f"LN_{ln_class}_{comp.id[:6]}"
        ET.SubElement(fn, "LNode", iedType=self.ied_name,
                      ldInst="PROT", prefix="", lnClass=ln_class, lnType=ln_type)

    def _comp_to_eq_type(self, ctype: str) -> str:
        return {
            "circuit_breaker": "CBR", "disconnect_switch": "DIS",
            "load_break_switch": "DPS", "current_transformer": "CT",
            "voltage_transformer": "VT", "transformer_2w": "TXR",
            "transformer_3w": "TXR", "reactor": "REACTOR",
            "capacitor": "CAP", "generator": "GEN",
            "feeder_terminal": "CBR", "ground": "GND",
            "surge_arrester": "SAR", "fuse": "FUSE",
            "busbar": "BUS",
        }.get(ctype, "UNK")

    def to_string(self, sld: ExtractedSLD) -> str:
        root = ET.Element("SCL", nsmap={"scl": self.NS})
        ET.SubElement(root, "Header", id=str(uuid.uuid4())[:8],
                      version="1.0", revision="2007B", toolID="SLD Interpreter v0.1")
        sub = self._build_substation(root, sld)
        root.append(sub)
        buf = io.BytesIO()
        ET.ElementTree(root).write(buf, xml_declaration=True, encoding="UTF-8", pretty_print=True)
        return buf.getvalue().decode("utf-8")

def export_sld_to_scl(sld: ExtractedSLD, output_path: str | Path, ied_name: str = "PROT_01") -> Path:
    return SCLExporter(ied_name=ied_name).export(sld, output_path)
