#!/usr/bin/env python3
"""Compare LLava vs Gemini extraction performance and accuracy."""

import json
import time
from pathlib import Path
import statistics

def evaluate_extraction(extracted_json: dict, reference_json: dict = None) -> dict:
    """
    Evaluate extraction quality.
    
    Args:
        extracted_json: Extracted SLD components
        reference_json: Ground truth (if available for accuracy calculation)
    
    Returns:
        Metrics dict with completeness and accuracy scores
    """
    
    metrics = {
        "component_counts": {
            "sources": len(extracted_json.get("sources", [])),
            "transformers": len(extracted_json.get("transformers", [])),
            "feeders": len(extracted_json.get("feeders", [])),
            "buses": len(extracted_json.get("buses", [])),
            "connections": len(extracted_json.get("connections", [])),
        },
        "total_components": sum(
            len(extracted_json.get(key, []))
            for key in ["sources", "transformers", "feeders", "buses"]
        ),
        "total_edges": len(extracted_json.get("connections", [])),
    }
    
    if reference_json:
        # Calculate precision/recall/F1 if ground truth available
        extracted_components = metrics["total_components"]
        reference_components = sum(
            len(reference_json.get(key, []))
            for key in ["sources", "transformers", "feeders", "buses"]
        )
        
        # Simplified accuracy (assumes 1:1 matching)
        if extracted_components > 0 and reference_components > 0:
            precision = min(extracted_components, reference_components) / extracted_components
            recall = min(extracted_components, reference_components) / reference_components
            f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
            
            metrics["precision"] = precision
            metrics["recall"] = recall
            metrics["f1_score"] = f1
    
    return metrics


def compare_models(image_path: str):
    """
    Compare LLava and Gemini on a single SLD.
    
    Args:
        image_path: Path to SLD image
    """
    
    print("\n" + "=" * 80)
    print(f"MODEL COMPARISON: {Path(image_path).name}")
    print("=" * 80)
    
    results = {
        "image": Path(image_path).name,
        "models": {}
    }
    
    # Test LLava
    print("\n[1/2] Testing LLava (Local via Ollama)...")
    try:
        from extract_llava import extract_with_llava
        start = time.time()
        llava_result = extract_with_llava(image_path)
        llava_time = time.time() - start
        
        if llava_result["status"] == "success":
            llava_metrics = evaluate_extraction(llava_result["data"])
            results["models"]["llava"] = {
                "status": "success",
                "time_seconds": llava_time,
                "metrics": llava_metrics,
            }
            print(f"     ✅ Success ({llava_time:.1f}s)")
            print(f"        Components: {llava_metrics['component_counts']}")
        else:
            results["models"]["llava"] = {
                "status": "failed",
                "error": llava_result.get("error"),
            }
            print(f"     ❌ Failed: {llava_result.get('error')}")
    except Exception as e:
        results["models"]["llava"] = {"status": "error", "error": str(e)}
        print(f"     ❌ Error: {e}")
    
    # Test Gemini
    print("\n[2/2] Testing Gemini (Cloud API)...")
    try:
        from extract import extract_with_gemini
        start = time.time()
        gemini_result = extract_with_gemini(image_path)
        gemini_time = time.time() - start
        
        if gemini_result["status"] == "success":
            gemini_metrics = evaluate_extraction(gemini_result["data"])
            results["models"]["gemini"] = {
                "status": "success",
                "time_seconds": gemini_time,
                "metrics": gemini_metrics,
            }
            print(f"     ✅ Success ({gemini_time:.1f}s)")
            print(f"        Components: {gemini_metrics['component_counts']}")
        else:
            results["models"]["gemini"] = {
                "status": "failed",
                "error": gemini_result.get("error"),
            }
            print(f"     ❌ Failed: {gemini_result.get('error')}")
    except Exception as e:
        results["models"]["gemini"] = {"status": "error", "error": str(e)}
        print(f"     ❌ Error: {e}")
    
    # Comparison
    print("\n" + "=" * 80)
    print("COMPARISON RESULTS")
    print("=" * 80)
    
    if "llava" in results["models"] and "gemini" in results["models"]:
        llava_status = results["models"]["llava"]["status"]
        gemini_status = results["models"]["gemini"]["status"]
        
        if llava_status == "success" and gemini_status == "success":
            llava_time = results["models"]["llava"]["time_seconds"]
            gemini_time = results["models"]["gemini"]["time_seconds"]
            
            print(f"\n⏱️  Processing Time:")
            print(f"   LLava: {llava_time:.1f}s")
            print(f"   Gemini: {gemini_time:.1f}s")
            if llava_time < gemini_time:
                print(f"   → LLava is {gemini_time/llava_time:.1f}x faster")
            else:
                print(f"   → Gemini is {llava_time/gemini_time:.1f}x faster")
            
            print(f"\n📊 Component Extraction:")
            llava_total = results["models"]["llava"]["metrics"]["total_components"]
            gemini_total = results["models"]["gemini"]["metrics"]["total_components"]
            print(f"   LLava: {llava_total} components")
            print(f"   Gemini: {gemini_total} components")
            if llava_total > gemini_total:
                print(f"   → LLava found {llava_total - gemini_total} more")
            elif gemini_total > llava_total:
                print(f"   → Gemini found {gemini_total - llava_total} more")
            else:
                print(f"   → Both extracted same count")
            
            print(f"\n💰 Cost Estimate (per SLD):")
            print(f"   LLava: $0.00 (Local, no API calls)")
            print(f"   Gemini: ~$0.10-$0.50 (Cloud API, quota-limited)")
            
            print(f"\n∞ Scalability:")
            print(f"   LLava: ∞ (No API limits, can process thousands locally)")
            print(f"   Gemini: Limited (Free tier: 20/day, paid tier: higher but costly)")
    
    print("\n" + "=" * 80)
    return results


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python compare_models.py <image_path>")
        print("\nExample:")
        print("  python compare_models.py data/real/katra.jpg")
        sys.exit(1)
    
    image_path = sys.argv[1]
    results = compare_models(image_path)
    
    # Save comparison results
    output_file = Path("results") / "model_comparison.json"
    output_file.parent.mkdir(exist_ok=True)
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n📁 Results saved: {output_file}")
