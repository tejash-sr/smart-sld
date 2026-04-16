#!/usr/bin/env python3
"""Extract SLD components using Gemini 2.5 Flash vision API."""

import google.generativeai as genai
import PIL.Image
import json
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    print("❌ Error: GEMINI_API_KEY not found in .env")
    print("   Steps:")
    print("   1. cp .env.example .env")
    print("   2. Add your Gemini API key: GEMINI_API_KEY=your_key")
    exit(1)

# Configure API
genai.configure(api_key=api_key)
model = genai.GenerativeModel("gemini-2.5-flash")

# Load image - support both .png and .jpg
img_candidates = [Path("data/real/katra.png"), Path("data/real/katra.jpg")]
img_path = None
for candidate in img_candidates:
    if candidate.exists():
        img_path = candidate
        break

if not img_path:
    print(f"❌ Error: No image found in data/real/. Checked: {[str(p) for p in img_candidates]}")
    exit(1)

print(f"📸 Loading image: {img_path}")
img = PIL.Image.open(img_path)

# Extraction prompt
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

print("🔄 Sending to Gemini 2.5-Flash...")
response = model.generate_content([prompt, img])

# Parse response - handle markdown wrapping
print("✅ Response received")
response_text = response.text

# Remove markdown code fence if present
if response_text.startswith("```json"):
    response_text = response_text[7:]
if response_text.startswith("```"):
    response_text = response_text[3:]
if response_text.endswith("```"):
    response_text = response_text[:-3]

response_text = response_text.strip()

try:
    result = json.loads(response_text)
    print(f"✅ JSON parsed successfully")
    print(f"   Sources: {len(result.get('sources', []))}")
    print(f"   Transformers: {len(result.get('transformers', []))}")
    print(f"   Feeders: {len(result.get('feeders', []))}")
    print(f"   Buses: {len(result.get('buses', []))}")
    print(f"   Connections: {len(result.get('connections', []))}")
except json.JSONDecodeError as e:
    print("❌ Failed to parse JSON. Raw response:")
    print(response.text)
    print(f"\nError: {e}")
    exit(1)

# Save output
output_path = Path("data/real/katra_output.json")
with open(output_path, "w") as f:
    json.dump(result, f, indent=2)

print(f"✅ Saved to {output_path}")
print("\n📋 Full extraction:")
print(json.dumps(result, indent=2))
