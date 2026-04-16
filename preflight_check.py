#!/usr/bin/env python3
"""Pre-flight check - Verify all dependencies and paths."""

import sys
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

print("=" * 60)
print("PRE-FLIGHT CHECK FOR KATRA SLD EXTRACTION")
print("=" * 60)

# Test 1: Core imports
print("\n[1] Testing core imports...")
try:
    import google.generativeai
    print("    ✅ google.generativeai OK")
except ImportError as e:
    print(f"    ❌ google.generativeai: {e}")
    sys.exit(1)

try:
    import PIL.Image
    print("    ✅ PIL.Image OK")
except ImportError as e:
    print(f"    ❌ PIL.Image: {e}")
    sys.exit(1)

try:
    import json
    print("    ✅ json OK")
except ImportError as e:
    print(f"    ❌ json: {e}")
    sys.exit(1)

try:
    from pathlib import Path
    print("    ✅ pathlib.Path OK")
except ImportError as e:
    print(f"    ❌ pathlib: {e}")
    sys.exit(1)

# Test 2: Environment variables
print("\n[2] Checking environment configuration...")
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    print("    ❌ GEMINI_API_KEY not set in .env")
    sys.exit(1)
print("    ✅ GEMINI_API_KEY configured")

# Test 3: File structure
print("\n[3] Checking file structure...")
image_candidates = [Path("data/real/katra.png"), Path("data/real/katra.jpg")]
found_image = False
for img in image_candidates:
    if img.exists():
        print(f"    ✅ Found image: {img}")
        found_image = True
        break

if not found_image:
    print(f"    ❌ Image not found. Checked: {image_candidates}")
    sys.exit(1)

output_dir = Path("data/real")
if output_dir.exists():
    print(f"    ✅ Output directory exists: {output_dir}")
else:
    print(f"    ❌ Output directory missing: {output_dir}")
    sys.exit(1)

# Test 4: Extract script
print("\n[4] Checking extract.py...")
extract_path = Path("scripts/extract.py")
if extract_path.exists():
    print(f"    ✅ Extract script exists: {extract_path}")
else:
    print(f"    ❌ Extract script missing: {extract_path}")
    sys.exit(1)

# Test 5: API key configuration
print("\n[5] Testing API key configuration...")
try:
    import google.generativeai as genai
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-2.5-flash")
    print("    ✅ API key configured, model initialized")
except Exception as e:
    print(f"    ❌ API configuration failed: {e}")
    sys.exit(1)

print("\n" + "=" * 60)
print("✅ ALL CHECKS PASSED")
print("=" * 60)
print("\nReady to extract KATRA SLD with Gemini API!")
print("Run: python scripts/extract.py")
