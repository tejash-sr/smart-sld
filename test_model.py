#!/usr/bin/env python
"""Test if YOLO model loads correctly."""
from pathlib import Path
from src.cv.detector import SymbolDetector
import cv2
import numpy as np

# Check if model file exists
model_path = Path("src/models/sld_detector.pt")
print(f"✅ Model file exists: {model_path.exists()}")
print(f"📁 Model path: {model_path.absolute()}")
if model_path.exists():
    print(f"📊 Model size: {model_path.stat().st_size / 1024 / 1024:.1f} MB")

# Try to load it
try:
    detector = SymbolDetector(model_path=str(model_path), confidence_threshold=0.5)
    print(f"✅ Detector created successfully")
    
    # Load and ensure model is initialized
    test_image = np.zeros((640, 640, 3), dtype=np.uint8)
    detector._ensure_loaded()
    
    print(f"✅ Model loaded: {detector._loaded}")
    print(f"✅ Model object exists: {detector.model is not None}")
    
    if detector.model:
        print(f"✅ YOLO MODEL READY FOR DETECTION!")
        print(f"   Model type: {type(detector.model)}")
    else:
        print(f"❌ Model is None")
        
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
