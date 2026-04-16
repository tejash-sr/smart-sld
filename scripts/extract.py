#!/usr/bin/env python3
"""Extract SLD components using Gemini 2.5 Flash vision API."""

import google.generativeai as genai
import PIL.Image
import json
import os
import time
from pathlib import Path
from dotenv import load_dotenv


def extract_with_gemini(image_path: str) -> dict:
    """
    Extract SLD components using Gemini 2.5-Flash.
    
    Args:
        image_path: Path to SLD image
    
    Returns:
        Dictionary with status and extracted components
    """
    
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    
    if not api_key:
        return {
            "status": "error",
            "error": "GEMINI_API_KEY not found in environment",
            "model": "gemini",
        }
    
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-2.5-flash")
    
    img_path = Path(image_path)
    if not img_path.exists():
        return {
            "status": "error",
            "error": f"Image not found: {image_path}",
            "model": "gemini",
        }
    
    img = PIL.Image.open(img_path)
    
    prompt = """You are an expert electrical engineer. Extract ALL components from this Single Line Diagram (SLD).

Return ONLY valid JSON (no markdown, no code blocks, no commentary):
{
  "sources": [
    {"id": "S1", "name": "132KV Fatuha Incomer", "voltage": "132kV"},
    {"id": "S2", "name": "132KV Gaighat", "voltage": "132kV"}
  ],
  "transformers": [
    {"id": "T1", "name": "ICT-1", "rating": "50MVA", "hv_side": "132kV", "lv_side": "33kV"},
    {"id": "T2", "name": "ICT-2", "rating": "50MVA", "hv_side": "132kV", "lv_side": "33kV"}
  ],
  "feeders": [
    {"id": "F1", "name": "Pahari", "voltage": "33kV"},
    {"id": "F2", "name": "Sabalpur", "voltage": "33kV"},
    {"id": "F3", "name": "Idle", "voltage": "33kV"}
  ],
  "buses": [
    {"id": "B1", "name": "132KV Main Bus", "voltage_level": "132kV"},
    {"id": "B2", "name": "132KV Transfer Bus", "voltage_level": "132kV"},
    {"id": "B3", "name": "33KV Main Bus", "voltage_level": "33kV"},
    {"id": "B4", "name": "33KV Transfer Bus", "voltage_level": "33kV"}
  ],
  "connections": [
    {"from": "S1", "to": "B1"},
    {"from": "B1", "to": "T1"},
    {"from": "T1", "to": "B3"}
  ]
}

Include ALL visible feeders, all transformers, all buses, all sources, and all connections you can identify."""

    start_time = time.time()
    try:
        response = model.generate_content([prompt, img])
        elapsed = time.time() - start_time
        
        response_text = response.text.strip()
        
        # Remove markdown wrapping
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.startswith("```"):
            response_text = response_text[3:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]
        
        response_text = response_text.strip()
        
        result = json.loads(response_text)
        return {
            "status": "success",
            "data": result,
            "model": "gemini",
            "processing_time_seconds": elapsed,
            "component_counts": {
                "sources": len(result.get("sources", [])),
                "transformers": len(result.get("transformers", [])),
                "feeders": len(result.get("feeders", [])),
                "buses": len(result.get("buses", [])),
                "connections": len(result.get("connections", [])),
            }
        }
    except json.JSONDecodeError as e:
        elapsed = time.time() - start_time
        return {
            "status": "parse_error",
            "error": f"Failed to parse JSON: {e}",
            "model": "gemini",
            "processing_time_seconds": elapsed,
        }
    except Exception as e:
        elapsed = time.time() - start_time
        return {
            "status": "error",
            "error": str(e),
            "model": "gemini",
            "processing_time_seconds": elapsed,
        }


def main():
    """CLI interface for single SLD extraction."""
    import sys
    
    # Load environment variables
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    
    if not api_key:
        print("❌ Error: GEMINI_API_KEY not found in .env")
        print("   Steps:")
        print("   1. cp .env.example .env")
        print("   2. Add your Gemini API key: GEMINI_API_KEY=your_key")
        sys.exit(1)
    
    # Find image if none specified
    if len(sys.argv) < 2:
        img_candidates = [Path("data/real/katra.png"), Path("data/real/katra.jpg")]
        img_path = None
        for candidate in img_candidates:
            if candidate.exists():
                img_path = candidate
                break
        
        if not img_path:
            print(f"❌ Error: No image found. Checked: {[str(p) for p in img_candidates]}")
            sys.exit(1)
    else:
        img_path = sys.argv[1]
    
    print("\n" + "=" * 70)
    print("Gemini 2.5-Flash SLD Extraction")
    print("=" * 70)
    
    result = extract_with_gemini(str(img_path))
    
    if result["status"] == "success":
        print(f"✅ Extraction Successful ({result['processing_time_seconds']:.1f}s)")
        print(f"   Sources: {result['component_counts']['sources']}")
        print(f"   Transformers: {result['component_counts']['transformers']}")
        print(f"   Feeders: {result['component_counts']['feeders']}")
        print(f"   Buses: {result['component_counts']['buses']}")
        print(f"   Connections: {result['component_counts']['connections']}")
        
        # Save output
        output_path = Path("data/real/katra_output.json")
        with open(output_path, "w") as f:
            json.dump(result["data"], f, indent=2)
        print(f"\n✅ Saved to {output_path}")
        print("\n📋 Full extraction:")
        print(json.dumps(result["data"], indent=2))
    else:
        print(f"❌ Extraction Failed: {result.get('error', 'Unknown error')}")
        sys.exit(1)
    
    print("=" * 70)


if __name__ == "__main__":
    main()
