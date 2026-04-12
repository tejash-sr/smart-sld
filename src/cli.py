#!/usr/bin/env python3
"""SLD Interpreter CLI - end-to-end command line interface.

Usage:
    python -m src.cli interpret <image_or_pdf>
    python -m src.cli batch <directory>
    python -m src.cli validate <sld_json>
    python -m src.cli export <sld_json> --format csv|graphml|scl --output <path>
    python -m src.cli serve --host 0.0.0.0 --port 8000

Examples:
    python -m src.cli interpret data/synthetic/sld_000.png
    python -m src.cli batch data/synthetic/ --output results/
    python -m src.cli export results/sld_000.json --format scl --output results/sld_000.scl
"""
from __future__ import annotations
import argparse, json, sys, time, uuid, warnings
from pathlib import Path

warnings.filterwarnings("ignore", message=".*PADDLE_PDX_DISABLE.*")
warnings.filterwarnings("ignore", message=".*requests.*DependencyWarning.*")

from src.pipeline import SLDPipeline
from src.models.sld_schema import ExtractedSLD, Component, Connection
from src.exporters import export_to_csv, export_to_graphml, export_sld_to_scl

def cmd_interpret(args):
    pipeline = SLDPipeline(model_path=args.model or None)
    print(f"[SLD Interpreter] Processing: {args.input}")
    t0 = time.time()
    sld = pipeline.interpret(args.input)
    elapsed = time.time() - t0

    print(f"  ✓ {len(sld.components)} components, {len(sld.connections)} connections")
    print(f"  ✓ Voltage levels: {', '.join(sld.voltage_levels)}")
    print(f"  ✓ Validation: {'PASS' if sld.validation.is_valid else 'FAIL'} ({len(sld.validation.issues)} issues)")
    print(f"  ✓ Processing time: {elapsed*1000:.0f}ms")
    print(f"  ✓ Buses detected: {len(sld.buses)}")

    for issue in sld.validation.issues:
        prefix = "✗" if issue.severity.value == "error" else "!"
        print(f"  {prefix} [{issue.rule_name}] {issue.message}")

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w") as f:
            json.dump(sld.to_dict(), f, indent=2, default=str)
        print(f"  → Saved to: {out_path}")
    else:
        print("\n" + json.dumps(sld.to_dict(), indent=2, default=str))

def cmd_batch(args):
    pipeline = SLDPipeline(model_path=args.model or None)
    input_path = Path(args.input_dir)
    output_dir = Path(args.output)

    # Find images
    patterns = ["*.png", "*.jpg", "*.jpeg", "*.pdf", "*.bmp", "*.tiff"]
    files = []
    for p in patterns:
        files.extend(sorted(input_path.glob(p)))
        files.extend(sorted(input_path.glob(f"*/{p}")))
    files = list(dict.fromkeys(files))  # dedupe

    if not files:
        print(f"No image files found in {args.input_dir}")
        return

    print(f"Batch processing {len(files)} files...")
    results = []
    for i, f in enumerate(files):
        t0 = time.time()
        try:
            sld = pipeline.interpret(f)
            elapsed = time.time() - t0
            result = {"file": str(f), "status": "ok", "components": len(sld.components),
                      "connections": len(sld.connections), "time_ms": int(elapsed*1000),
                      "valid": sld.validation.is_valid}
            print(f"  [{i+1}/{len(files)}] {f.name}: {len(sld.components)} comp, {elapsed*1000:.0f}ms")
        except Exception as e:
            result = {"file": str(f), "status": "error", "error": str(e)}
            print(f"  [{i+1}/{len(files)}] {f.name}: ERROR - {e}")

        results.append(result)

        if args.output:
            stem = f.stem
            json_path = output_dir / f"{stem}_result.json"
            if result["status"] == "ok":
                with open(json_path, "w") as fp:
                    json.dump(sld.to_dict(), fp, indent=2, default=str)

    # Summary
    ok_count = sum(1 for r in results if r["status"] == "ok")
    total_time = sum(r.get("time_ms", 0) for r in results)
    print(f"\nBatch complete: {ok_count}/{len(files)} succeeded, {total_time}ms total")
    if args.json_summary:
        with open(args.json_summary, "w") as f:
            json.dump(results, f, indent=2)

def cmd_validate(args):
    with open(args.sld_json) as f:
        data = json.load(f)
    sld = ExtractedSLD(**data)
    print(f"Validating: {sld.source_filename}")
    print(f"  Components: {len(sld.components)}")
    print(f"  Connections: {len(sld.connections)}")
    print(f"  Validation: {'VALID' if sld.validation.is_valid else 'INVALID'}")
    for issue in (sld.validation.issues or []):
        print(f"  [{issue.severity.value}] {issue.rule_name}: {issue.message}")

def cmd_export(args):
    with open(args.sld_json) as f:
        data = json.load(f)
    sld = ExtractedSLD(**data)
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if args.format == "csv":
        paths = export_to_csv(sld, out_path.parent)
        for k, p in paths.items():
            print(f"  → {k}: {p}")
    elif args.format == "graphml":
        p = export_to_graphml(sld, out_path)
        print(f"  → GraphML: {p}")
    elif args.format == "scl":
        p = export_sld_to_scl(sld, out_path, ied_name=args.ied or "PROT_01")
        print(f"  → SCL: {p}")
    elif args.format == "json":
        with open(out_path, "w") as f:
            json.dump(sld.to_dict(), f, indent=2, default=str)
        print(f"  → JSON: {out_path}")
    else:
        print(f"Unknown format: {args.format}")
        sys.exit(1)

def cmd_serve(args):
    import uvicorn
    from src.api import main as api_main
    print(f"Starting server on {args.host}:{args.port}")
    uvicorn.run(api_main.app, host=args.host, port=args.port, reload=args.reload)

def main():
    parser = argparse.ArgumentParser(prog="sld-interpreter", description="SLD Interpretation CLI")
    sub = parser.add_subparsers(dest="cmd")

    # interpret
    p_interp = sub.add_parser("interpret", help="Interpret a single SLD image/PDF")
    p_interp.add_argument("input", help="Input image or PDF file")
    p_interp.add_argument("--model", help="Path to YOLO model (.pt file)")
    p_interp.add_argument("--output", "-o", help="Output JSON file")

    # batch
    p_batch = sub.add_parser("batch", help="Batch process directory of SLDs")
    p_batch.add_argument("input_dir", help="Directory containing SLD images")
    p_batch.add_argument("--output", "-o", default="results/", help="Output directory for results")
    p_batch.add_argument("--model", help="Path to YOLO model")
    p_batch.add_argument("--json-summary", help="Save batch summary as JSON")

    # validate
    p_val = sub.add_parser("validate", help="Validate an extracted SLD JSON file")
    p_val.add_argument("sld_json", help="SLD JSON file from interpret")

    # export
    p_exp = sub.add_parser("export", help="Export SLD JSON to another format")
    p_exp.add_argument("sld_json", help="SLD JSON file")
    p_exp.add_argument("--format", "-f", choices=["csv", "graphml", "scl", "json"], default="json")
    p_exp.add_argument("--output", "-o", required=True, help="Output file path")
    p_exp.add_argument("--ied", help="IED name for SCL export")

    # serve
    p_serve = sub.add_parser("serve", help="Start FastAPI server")
    p_serve.add_argument("--host", default="0.0.0.0")
    p_serve.add_argument("--port", type=int, default=8000)
    p_serve.add_argument("--reload", action="store_true")

    args = parser.parse_args()

    if args.cmd == "interpret":
        cmd_interpret(args)
    elif args.cmd == "batch":
        cmd_batch(args)
    elif args.cmd == "validate":
        cmd_validate(args)
    elif args.cmd == "export":
        cmd_export(args)
    elif args.cmd == "serve":
        cmd_serve(args)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
