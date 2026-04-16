#!/usr/bin/env python3
"""Batch process multiple SLDs using LLava or Gemini."""

import json
import sys
from pathlib import Path
from datetime import datetime
import os

def run_batch(image_dir: str, model: str = "llava", output_dir: str = None):
    """
    Process all SLDs in a directory.
    
    Args:
        image_dir: Directory containing SLD images
        model: "llava" (local, unlimited) or "gemini" (cloud, quota-limited)
        output_dir: Directory to save JSON outputs (default: same as image_dir)
    """
    
    image_dir = Path(image_dir)
    if not image_dir.exists():
        print(f"❌ Directory not found: {image_dir}")
        return
    
    if output_dir is None:
        output_dir = image_dir
    else:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
    
    # Find all images
    images = sorted(image_dir.glob("*.jpg")) + sorted(image_dir.glob("*.png"))
    
    if not images:
        print(f"❌ No images found in {image_dir}")
        return
    
    print("\n" + "=" * 80)
    print(f"BATCH PROCESSING: {len(images)} images using {model.upper()}")
    print("=" * 80)
    
    results = {
        "batch_timestamp": datetime.now().isoformat(),
        "model": model,
        "total_images": len(images),
        "extractions": [],
        "summary": {
            "successful": 0,
            "failed": 0,
            "total_processing_time": 0,
        }
    }
    
    # Import appropriate extractor
    if model.lower() == "llava":
        from extract_llava import extract_with_llava
        extractor = extract_with_llava
    elif model.lower() == "gemini":
        try:
            from extract import extract_with_gemini
            extractor = extract_with_gemini
        except (ImportError, Exception) as e:
            print(f"❌ Gemini extraction not available: {e}")
            return
    else:
        print(f"❌ Unknown model: {model}. Use 'llava' or 'gemini'")
        return
    
    # Process each image
    for idx, img_path in enumerate(images, 1):
        print(f"\n[{idx}/{len(images)}] Processing: {img_path.name}")
        
        try:
            result = extractor(str(img_path))
            
            # Save output
            output_json = output_dir / f"{img_path.stem}_output.json"
            
            if result["status"] == "success":
                with open(output_json, "w") as f:
                    json.dump(result["data"], f, indent=2)
                
                results["extractions"].append({
                    "image": img_path.name,
                    "status": "success",
                    "output_file": str(output_json),
                    "component_counts": result["component_counts"],
                    "processing_time": result["processing_time_seconds"],
                })
                results["summary"]["successful"] += 1
                results["summary"]["total_processing_time"] += result["processing_time_seconds"]
                
                print(f"     ✅ Success ({result['processing_time_seconds']:.1f}s)")
                print(f"        Components: {result['component_counts']}")
                print(f"        Output: {output_json}")
            else:
                results["extractions"].append({
                    "image": img_path.name,
                    "status": "failed",
                    "error": result.get("error", "Unknown error"),
                })
                results["summary"]["failed"] += 1
                print(f"     ❌ Failed: {result.get('error', 'Unknown error')}")
        
        except Exception as e:
            results["extractions"].append({
                "image": img_path.name,
                "status": "error",
                "error": str(e),
            })
            results["summary"]["failed"] += 1
            print(f"     ❌ Error: {e}")
    
    # Save batch results
    batch_summary = output_dir / f"batch_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(batch_summary, "w") as f:
        json.dump(results, f, indent=2)
    
    # Print summary
    print("\n" + "=" * 80)
    print("BATCH SUMMARY")
    print("=" * 80)
    print(f"✅ Successful: {results['summary']['successful']}")
    print(f"❌ Failed: {results['summary']['failed']}")
    print(f"⏱️  Total time: {results['summary']['total_processing_time']:.1f}s")
    avg_time = results['summary']['total_processing_time'] / len(images) if images else 0
    print(f"📊 Average time per image: {avg_time:.1f}s")
    print(f"📁 Results saved: {batch_summary}")
    print("=" * 80)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python batch_process.py <image_dir> [model] [output_dir]")
        print("\nExamples:")
        print("  # Process with LLava (local, unlimited)")
        print("  python batch_process.py data/real/")
        print("  python batch_process.py data/real/ llava results/")
        print("\n  # Process with Gemini (cloud, faster but quota-limited)")
        print("  python batch_process.py data/real/ gemini results/")
        sys.exit(1)
    
    image_dir = sys.argv[1]
    model = sys.argv[2] if len(sys.argv) > 2 else "llava"
    output_dir = sys.argv[3] if len(sys.argv) > 3 else None
    
    run_batch(image_dir, model, output_dir)
