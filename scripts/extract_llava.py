#!/usr/bin/env python3
"""Extract SLD components using LLava via Ollama (local, no API limits)."""

import ollama
import json
import base64
from pathlib import Path
from datetime import datetime
import time

def extract_with_llava(image_path: str) -> dict:
    """
    Extract SLD components using LLava vision model via Ollama.
    
    Args:
        image_path: Path to SLD image (PNG/JPG)
    
    Returns:
        Dictionary with extracted components (sources, transformers, feeders, buses, connections)
    """
    
    img_path = Path(image_path)
    if not img_path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")
    
    print(f"📸 Loading image: {img_path}")
    
    # Read image and encode to base64
    with open(img_path, "rb") as f:
        image_data = base64.b64encode(f.read()).decode("utf-8")
    
    # System prompt for electrical SLD extraction
    system_prompt = """You are an expert electrical engineer. Extract ALL components from this Single Line Diagram (SLD).

Return ONLY valid JSON (no markdown, no code blocks, no commentary). Include every component you can identify:
- Sources: Incoming supplies (incomers), generators
- Transformers: Power transformers, voltage regulators
- Buses: Busbars, switchboards, collection points
- Feeders: Outgoing lines to loads, substations, distribution
- Connections: All lines connecting these components

JSON structure:
{
  "sources": [{"id": "S1", "name": "...", "voltage": "...kV", "type": "incomer|generator"}],
  "transformers": [{"id": "T1", "name": "...", "rating": "...MVA", "hv_side": "...kV", "lv_side": "...kV"}],
  "feeders": [{"id": "F1", "name": "...", "voltage": "...kV", "destination": "..."}],
  "buses": [{"id": "B1", "name": "...", "voltage_level": "...kV"}],
  "connections": [{"from": "S1", "to": "B1"}]
}"""

    print("🔄 Sending to LLava via Ollama...")
    start_time = time.time()
    
    try:
        response = ollama.generate(
            model="llava",
            prompt=system_prompt + "\n\nExtract the SLD components from this image.",
            images=[image_data],
            stream=False,
        )
        
        elapsed = time.time() - start_time
        response_text = response["response"].strip()
        
        # Remove markdown wrapping if present
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.startswith("```"):
            response_text = response_text[3:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]
        
        response_text = response_text.strip()
        
        print(f"✅ Response received ({elapsed:.1f}s)")
        
        try:
            result = json.loads(response_text)
            return {
                "status": "success",
                "data": result,
                "model": "llava",
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
            return {
                "status": "parse_error",
                "error": f"Failed to parse JSON: {e}",
                "raw_response": response_text[:500],
                "model": "llava",
                "processing_time_seconds": elapsed,
            }
    
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "model": "llava",
        }


def main():
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python extract_llava.py <image_path> [output_json]")
        print("\nExample:")
        print("  python extract_llava.py data/real/katra.jpg data/real/katra_llava.json")
        sys.exit(1)
    
    image_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else None
    
    print("\n" + "=" * 70)
    print("LLava SLD Extraction via Ollama (Local, No API Limits)")
    print("=" * 70)
    
    result = extract_with_llava(image_path)
    
    if result["status"] == "success":
        print("\n✅ Extraction Successful!")
        print(f"   Components: {result['component_counts']}")
        
        if output_path:
            with open(output_path, "w") as f:
                json.dump(result["data"], f, indent=2)
            print(f"   Saved: {output_path}")
        else:
            print("\n📋 Extracted Data:")
            print(json.dumps(result["data"], indent=2))
    else:
        print(f"\n❌ Extraction Failed: {result.get('error', 'Unknown error')}")
        if "raw_response" in result:
            print(f"   Raw: {result['raw_response']}")
    
    elapsed = result.get('processing_time_seconds', 'N/A')
    if isinstance(elapsed, (int, float)):
        print(f"\n⏱️  Processing time: {elapsed:.1f}s")
    else:
        print(f"\n⏱️  Processing time: {elapsed}s")
    print("=" * 70)


if __name__ == "__main__":
    main()
