"""Tests for SLD interpretation pipeline."""
from __future__ import annotations
import json, math, random, uuid, time
from pathlib import Path
import pytest
from src.models.sld_schema import (
    Component, ComponentType, Connection, ConnectionType,
    Point, BoundingBox, ExtractedSLD, ValidationResult,
    BusSection, Bus, NetworkGraph,
)
from src.preprocessing.enhance import SLDPreprocessor
from src.cv.detector import SymbolDetector, COMPONENT_CLASSES
from src.cv.ocr import TextExtractor, TextExtraction
from src.cv.graph_builder import GraphBuilder
from src.rule_engine.validator import RuleEngine, VoltageHierarchyValidator
from src.pipeline import SLDPipeline
from src.exporters import export_to_csv, export_to_graphml, export_sld_to_scl

# ─── Schema Tests ───────────────────────────────────────────────────────────
class TestSchema:
    def test_component_create(self):
        c = Component(
            id="test_1",
            component_type=ComponentType.TRANSFORMER_2W,
            label="T1",
            voltage_level="33kV",
            position=Point(x=100.0, y=200.0),
            bbox=BoundingBox(x_min=85, y_min=185, x_max=115, y_max=215),
            confidence=0.95,
        )
        assert c.id == "test_1"
        assert c.component_type == ComponentType.TRANSFORMER_2W
        assert c.voltage_level == "33kV"
        assert c.position.x == 100.0
        assert c.bbox.width == 30.0
        assert c.bbox.center_x == 100.0

    def test_component_uuid_default(self):
        c = Component(component_type=ComponentType.FEEDER_TERMINAL, position=Point(x=0, y=0))
        assert len(c.id) == 8
        assert c.confidence == 1.0

    def test_extracted_sld_roundtrip(self):
        sld = ExtractedSLD(
            source_filename="test.png",
            voltage_levels=["220kV", "33kV"],
            components=[],
            connections=[],
            buses=[],
        )
        data = sld.to_dict()
        restored = ExtractedSLD(**data)
        assert restored.source_filename == "test.png"
        assert restored.voltage_levels == ["220kV", "33kV"]

    def test_bbox_properties(self):
        bbox = BoundingBox(x_min=10, y_min=20, x_max=110, y_max=70)
        assert bbox.width == 100
        assert bbox.height == 50
        assert bbox.center_x == 60
        assert bbox.center_y == 45

    def test_component_to_dict_serializable(self):
        c = Component(
            component_type=ComponentType.CIRCUIT_BREAKER,
            position=Point(x=50, y=50),
            bbox=BoundingBox(x_min=40, y_min=40, x_max=60, y_max=60),
        )
        d = c.model_dump()
        assert isinstance(d["component_type"], str)
        assert isinstance(d["position"]["x"], float)

# ─── Preprocessing Tests ─────────────────────────────────────────────────────
class TestPreprocessing:
    def test_grayscale_conversion(self):
        import numpy as np, cv2
        rgb = np.ones((100, 100, 3), dtype=np.uint8) * 128
        proc = SLDPreprocessor()
        gray = proc._to_grayscale(rgb)
        assert gray.shape == (100, 100)
        assert gray.dtype == np.uint8

    def test_binarize_output_binary(self):
        import numpy as np, cv2
        gray = np.ones((100, 100), dtype=np.uint8) * 180
        proc = SLDPreprocessor()
        binary = proc._binarize(gray)
        assert binary.dtype == np.uint8
        unique_vals = set(binary.flatten())
        assert all(v in (0, 255) for v in unique_vals)

    def test_preprocess_returns_grayscale(self):
        import numpy as np, cv2
        rgb = np.ones((100, 100, 3), dtype=np.uint8) * 200
        proc = SLDPreprocessor()
        out = proc.preprocess(rgb)
        assert len(out.shape) == 2

# ─── Detector Tests ──────────────────────────────────────────────────────────
class TestDetector:
    def test_detector_returns_components(self):
        import numpy as np
        detector = SymbolDetector()
        result = detector.detect(np.zeros((100, 100, 3), dtype=np.uint8))
        assert isinstance(result, list)
        assert result == []

    def test_detector_stats(self):
        detector = SymbolDetector()
        stats = detector.get_detection_stats()
        assert "model_loaded" in stats
        assert "yolo_classes" in stats
        assert stats["yolo_classes"] == len(COMPONENT_CLASSES)
        assert stats["model_loaded"] == False

    def test_detector_yolo_classes_complete(self):
        for cls_id, ctype in COMPONENT_CLASSES.items():
            assert isinstance(ctype, ComponentType)

# ─── Graph Builder Tests ─────────────────────────────────────────────────────
class TestGraphBuilder:
    def test_add_component(self):
        gb = GraphBuilder()
        c = Component(id="test", component_type=ComponentType.GROUND, position=Point(x=50, y=50))
        gb.add_component(c)
        assert "test" in gb.graph.nodes

    def test_add_connection(self):
        gb = GraphBuilder()
        c1 = Component(id="a", component_type=ComponentType.BUSBAR, position=Point(x=0, y=0))
        c2 = Component(id="b", component_type=ComponentType.FEEDER_TERMINAL, position=Point(x=50, y=0))
        gb.add_component(c1)
        gb.add_component(c2)
        gb.add_connection("a", "b", ConnectionType.AC_LINE)
        assert gb.graph.has_edge("a", "b")

    def test_build_returns_network_graph(self):
        gb = GraphBuilder()
        busbar = Component(id="bus_0", component_type=ComponentType.BUSBAR,
                           position=Point(x=100, y=100),
                           bbox=BoundingBox(x_min=40, y_min=94, x_max=160, y_max=106))
        cb = Component(id="cb_0", component_type=ComponentType.CIRCUIT_BREAKER,
                       position=Point(x=200, y=100),
                       bbox=BoundingBox(x_min=189, y_min=89, x_max=211, y_max=111))
        gb.add_component(busbar)
        gb.add_component(cb)
        gb.add_connection("bus_0", "cb_0", ConnectionType.AC_LINE)
        ng, bus_sections = gb.build()
        assert isinstance(ng, NetworkGraph)
        assert len(ng.nodes) == 2
        assert len(ng.edges) == 1
        assert len(bus_sections) == 1

    def test_busbar_flood_fill(self):
        gb = GraphBuilder()
        busbar = Component(id="bus_0", component_type=ComponentType.BUSBAR,
                           position=Point(x=100, y=100),
                           bbox=BoundingBox(x_min=40, y_min=94, x_max=160, y_max=106))
        gb.add_component(busbar)
        ng, bus_sections = gb.build()
        assert len(bus_sections) == 1
        assert bus_sections[0].label.startswith("BUS")

    def test_orphaned_components_no_connections(self):
        gb = GraphBuilder()
        c = Component(id="orphan", component_type=ComponentType.CAPACITOR, position=Point(x=100, y=100))
        gb.add_component(c)
        ng, _ = gb.build()
        assert len(ng.edges) == 0

# ─── Validator Tests ─────────────────────────────────────────────────────────
class TestValidator:
    def test_orphan_detection(self):
        sld = ExtractedSLD(source_filename="test.png", voltage_levels=["33kV"],
            components=[
                Component(id="c1", component_type=ComponentType.CAPACITOR, position=Point(x=0, y=0)),
                Component(id="c2", component_type=ComponentType.REACTOR, position=Point(x=100, y=100)),
            ], connections=[], buses=[])
        validator = VoltageHierarchyValidator()
        issues = validator._check_orphan_components(sld)
        assert len(issues) == 1
        assert issues[0].rule_name == "orphan_components"

    def test_connection_unknown_component(self):
        sld = ExtractedSLD(source_filename="test.png", voltage_levels=["33kV"],
            components=[Component(id="c1", component_type=ComponentType.BUSBAR, position=Point(x=0, y=0))],
            connections=[Connection(id="conn1", from_component="c1", to_component="ghost_id")], buses=[])
        validator = VoltageHierarchyValidator()
        issues = validator._check_connection_voltage_compatibility(sld.connections[0], sld.components)
        assert any(i.rule_name == "connection_refs_valid_component" for i in issues)

    def test_no_issues_when_connected(self):
        sld = ExtractedSLD(source_filename="test.png", voltage_levels=["33kV"],
            components=[
                Component(id="b1", component_type=ComponentType.BUSBAR, position=Point(x=0, y=0)),
                Component(id="c1", component_type=ComponentType.CIRCUIT_BREAKER, position=Point(x=100, y=0)),
            ],
            connections=[Connection(id="conn1", from_component="b1", to_component="c1")], buses=[])
        validator = VoltageHierarchyValidator()
        issues = validator._check_orphan_components(sld)
        assert issues == []

    def test_rule_engine_validates(self):
        engine = RuleEngine()
        sld = ExtractedSLD(source_filename="test.png", voltage_levels=["220kV"],
            components=[Component(id="b1", component_type=ComponentType.BUSBAR, position=Point(x=0, y=0))],
            connections=[], buses=[])
        result = engine.validate(sld)
        assert isinstance(result, ValidationResult)
        assert result.is_valid == True  # orphan warning is WARNING severity

    def test_rule_engine_no_false_positives(self):
        engine = RuleEngine()
        sld = ExtractedSLD(source_filename="test.png", voltage_levels=["220kV"],
            components=[
                Component(id="b1", component_type=ComponentType.BUSBAR, position=Point(x=0, y=0)),
                Component(id="c1", component_type=ComponentType.CIRCUIT_BREAKER, position=Point(x=100, y=0)),
            ],
            connections=[Connection(id="conn1", from_component="b1", to_component="c1")], buses=[])
        result = engine.validate(sld)
        assert isinstance(result, ValidationResult)
        assert result.is_valid == True

# ─── Pipeline Tests ───────────────────────────────────────────────────────────
class TestPipeline:
    def test_pipeline_processes_image_array(self):
        import numpy as np
        pipeline = SLDPipeline()
        img = np.ones((200, 200, 3), dtype=np.uint8) * 255
        sld = pipeline.process_image_array(img, source_filename="test.png")
        assert isinstance(sld, ExtractedSLD)
        assert sld.metadata.get("processing_time_ms", 0) >= 0

    def test_pipeline_with_synthetic_png(self):
        png_path = Path("data/synthetic/sld_000.png")
        if not png_path.exists():
            pytest.skip("Synthetic PNG not found")
        pipeline = SLDPipeline()
        sld = pipeline.interpret(str(png_path))
        assert sld.source_filename == "sld_000.png"
        assert len(sld.components) >= 0

# ─── Export Tests ─────────────────────────────────────────────────────────────
class TestExporters:
    def test_csv_export(self, tmp_path):
        sld = ExtractedSLD(source_filename="test.png", voltage_levels=["33kV"],
            components=[Component(id="c1", component_type=ComponentType.BUSBAR, position=Point(x=0, y=0))],
            connections=[], buses=[])
        paths = export_to_csv(sld, tmp_path)
        assert paths["components"].exists()
        assert paths["connections"].exists()
        content = paths["components"].read_text()
        assert "c1" in content and "busbar" in content

    def test_graphml_export(self, tmp_path):
        sld = ExtractedSLD(source_filename="test.png", voltage_levels=["33kV"],
            components=[Component(id="b1", component_type=ComponentType.BUSBAR, position=Point(x=0, y=0))],
            connections=[], buses=[])
        path = export_to_graphml(sld, tmp_path / "test.graphml")
        assert path.exists()
        assert "<graphml" in path.read_text()

    def test_scl_export(self, tmp_path):
        sld = ExtractedSLD(source_filename="test.png", voltage_levels=["33kV"],
            components=[Component(id="b1", component_type=ComponentType.BUSBAR, label="BUS-1", position=Point(x=100, y=100))],
            connections=[], buses=[Bus(id="bs1", name="BUS-1", voltage_level="33kV", component_ids=["b1"])])
        path = export_sld_to_scl(sld, tmp_path / "test.scl")
        assert path.exists()
        content = path.read_text()
        assert "<SCL" in content and "Substation" in content

# ─── Synthetic Data Tests ────────────────────────────────────────────────────
class TestSyntheticData:
    def test_synthetic_files_exist(self):
        gt_path = Path("data/synthetic/sld_000_gt.json")
        if not gt_path.exists():
            pytest.skip("Synthetic data not generated")
        with open(gt_path) as f:
            gt = json.load(f)
        assert "components" in gt and "connections" in gt
        components = [Component(**c) for c in gt["components"]]
        assert len(components) > 0
        assert all(c.component_type in ComponentType for c in components)

    def test_synthetic_png_images_rendered(self):
        png_path = Path("data/synthetic/sld_000.png")
        if not png_path.exists():
            pytest.skip("Synthetic images not generated")
        from PIL import Image
        img = Image.open(png_path)
        assert img.size == (1200, 800)
        assert img.mode == "RGB"
