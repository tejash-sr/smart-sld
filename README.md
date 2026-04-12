# SLD Interpreter

Production-grade system for interpreting electrical Single Line Diagrams (SLDs) and converting them into structured digital data.

## Quick Start

```bash
cd /home/workspace/sld-interpreter

# Interpret a single diagram
python -m src.cli interpret data/synthetic/sld_000.png -o result.json

# Batch process a directory
python -m src.cli batch data/synthetic/ --output results/

# Export to CSV / GraphML / IEC 61850 SCL
python -m src.cli export result.json -f csv -o outputs/
python -m src.cli export result.json -f scl -o outputs/sld.scl

# Validate extracted JSON
python -m src.cli validate result.json

# Start API server
python -m src.cli serve --port 8000
```

## Architecture

```
Input (PNG/JPG/PDF/DXF)
  │
  ▼
┌─────────────────────────────────────────────────────┐
│  Preprocessing (SLDPreprocessor)                    │
│  • Grayscale conversion                             │
│  • Deskew / rotation correction                      │
│  • Morphological binarization                       │
│  • Contrast enhancement                              │
└─────────────────────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────────────────────┐
│  CV Engine                                          │
│  ┌─────────────────┐  ┌─────────────────────────────┐│
│  │ SymbolDetector  │  │ TextExtractor (OCR)         ││
│  │ • YOLO (trainable)│ │ • PaddleOCR + Tesseract      ││
│  │ • Template match │  │ • Label-to-symbol matching  ││
│  └─────────────────┘  └─────────────────────────────┘│
│  ┌─────────────────┐  ┌─────────────────────────────┐│
│  │ LineDetector     │  │ DXFInterpreter (CAD)        ││
│  │ • Hough transform│  │ • ezdxf for .dxf/.dwg       ││
│  │ • Busbar detection│  │ • Block/symbol mapping       ││
│  └─────────────────┘  └─────────────────────────────┘│
└─────────────────────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────────────────────┐
│  GraphBuilder                                        │
│  • NetworkX graph construction                       │
│  • Flood-fill bus section detection                  │
│  • Proximity-based connection inference              │
└─────────────────────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────────────────────┐
│  RuleEngine                                          │
│  • Voltage hierarchy validation                     │
│  • Transformer pairing rules                         │
│  • Orphan connection detection                       │
└─────────────────────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────────────────────┐
│  Exporters                                           │
│  • JSON (ExtractedSLD schema)                        │
│  • CSV (components + connections)                    │
│  • GraphML (for yEd / Gephi / NetworkX)             │
│  • IEC 61850 SCL (SCADA integration)                │
└─────────────────────────────────────────────────────┘
```

## Project Structure

```
sld-interpreter/
├── src/
│   ├── models/sld_schema.py      # Pydantic domain models
│   ├── preprocessing/enhance.py # Image preprocessing pipeline
│   ├── cv/
│   │   ├── detector.py          # YOLO symbol detector + template fallback
│   │   ├── ocr.py               # PaddleOCR / Tesseract text extraction
│   │   ├── line_detector.py     # Hough line detection
│   │   ├── dxf_parser.py        # DXF/DWG CAD parser (ezdxf)
│   │   └── graph_builder.py     # NetworkX topology construction
│   ├── rule_engine/validator.py  # Domain validation rules
│   ├── exporters/
│   │   ├── graphml.py           # CSV + GraphML export
│   │   └── iec61850_scl.py      # IEC 61850 SCL XML export
│   ├── pipeline.py              # End-to-end orchestrator
│   ├── api/main.py              # FastAPI server
│   └── cli.py                   # Command line interface
├── scripts/
│   ├── generate_synthetic.py   # Generate labeled training data
│   └── train_yolo.py            # Train YOLO detector on synthetic data
├── data/
│   ├── synthetic/               # 50 labeled synthetic SLDs (PNG + JSON GT)
│   └── samples/sample_sld_output.json
└── hitl_frontend/
    └── index.html               # Standalone HITL review UI
```

## Output Schema

```json
{
  "version": "1.0",
  "extracted_at": "2026-04-11T16:00:00",
  "source_filename": "220kV_BusSection_Type1.png",
  "voltage_levels": ["400kV", "220kV", "33kV", "11kV"],
  "components": [
    {
      "id": "bus_0",
      "component_type": "busbar",
      "label": "BUS-1",
      "voltage_level": "415V",
      "position": {"x": 400.0, "y": 320.0},
      "bbox": {"x_min": 340, "y_min": 314, "x_max": 460, "y_max": 326},
      "confidence": 0.99
    }
  ],
  "connections": [
    {
      "id": "conn_abc123",
      "from_component": "comp_xyz",
      "to_component": "bus_0",
      "connection_type": "ac_line",
      "intermediate_points": [{"x": 500, "y": 320}]
    }
  ],
  "buses": [
    {"id": "bs1", "name": "BUS-1", "voltage_level": "415V", "component_ids": ["bus_0", "comp_xyz"]}
  ],
  "network_graph": { ... },
  "validation": {
    "is_valid": true,
    "issues": []
  },
  "confidence": {
    "avg_symbol_confidence": 0.92,
    "avg_ocr_confidence": 0.88,
    "avg_connectivity_confidence": 0.79
  },
  "metadata": {"processing_time_ms": 453}
}
```

## Training the Model

```bash
# 1. Generate synthetic labeled data (50 PNG + JSON ground truth pairs)
python scripts/generate_synthetic.py --output data/synthetic --n 50

# 2. Convert to YOLO format
python scripts/train_yolo.py --prepare-only --data data/synthetic --output data/yolo_dataset

# 3. Train YOLO (requires GPU)
python scripts/train_yolo.py \\
    --data data/yolo_dataset \\
    --output runs/detect/sld_v1 \\
    --epochs 100 --batch 16 --model yolov8m --device cuda

# 4. Use trained model
python -m src.cli interpret my_diagram.png --model runs/detect/sld_v1/weights/best.pt
```

## What's Working

| Component | Status | Notes |
|-----------|--------|-------|
| Preprocessing | ✅ | Grayscale, deskew, binarization, contrast |
| YOLO Detector | ⚠️ | Interface ready; needs trained .pt file |
| Template Matcher | ✅ | Fallback when no YOLO model loaded |
| OCR (PaddleOCR) | ✅ | Primary text extractor |
| OCR (Tesseract) | ✅ | Fallback text extractor |
| Line Detection | ✅ | Hough transform + busbar detection |
| DXF Parser | ✅ | ezdxf for vector CAD files |
| Graph Builder | ✅ | NetworkX + flood-fill bus detection |
| Rule Engine | ✅ | Voltage hierarchy validation |
| JSON Export | ✅ | Full ExtractedSLD schema |
| CSV Export | ✅ | Components + connections |
| GraphML Export | ✅ | For yEd / Gephi |
| IEC 61850 SCL | ✅ | SCADA integration format |
| CLI | ✅ | interpret / batch / validate / export / serve |
| FastAPI | ✅ | /interpret and /health endpoints |
| HITL Frontend | ✅ | https://tej24.zo.space/sld-review |

## What's Left (Requires Real Data)

1. **Train YOLO** — Run `scripts/train_yolo.py` on a GPU machine with real utility SLDs
2. **Label real diagrams** — Use CVAT or Label Studio to label 100-200 real SLD images
3. **Utility-specific symbols** — Build custom symbol templates per DISCOM/client
4. **Production backend** — Connect zo.space API route to running FastAPI service

## zo.space Deployment

- **HITL Review UI**: https://tej24.zo.space/sld-review
- **REST API**: https://tej24.zo.space/api/sld/interpret (POST file upload)

## Impact Targets

| Metric | Current (Manual) | With System |
|--------|-----------------|-------------|
| Time per SLD (40 components) | 4-8 hours | ~15-20 minutes |
| Error rate | 5-15% | <1% |
| Cost per SLD | $150-300 | $20-40 |
| Weekly SLD capacity | ~5-10 | 50-100+ |
