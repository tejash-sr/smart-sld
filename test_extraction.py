#!/usr/bin/env python
"""Test extraction with real YOLO model."""
import cv2
import numpy as np
import json
from src.pipeline import SLDPipeline

# Create pipeline with real YOLO model
print("🔧 Creating pipeline with YOLO model...")
pipeline = SLDPipeline(model_path="src/models/sld_detector.pt")
print(f"   Detector model loaded: {pipeline.detector._loaded}")
print(f"   Detector model object: {pipeline.detector.model}")

# Create a test image (640x640, BGR format) - must have 3 channels!
test_image = np.random.randint(0, 255, (640, 640, 3), dtype=np.uint8)
print(f"   Test image shape: {test_image.shape}, dtype: {test_image.dtype}")

# Run extraction
print("🚀 Running extraction with REAL YOLO model...")
try:
    sld = pipeline.process_image_array(test_image, source_filename="test.jpg")
    print(f"✅ Extraction complete!")
    print(f"   📊 Components detected: {len(sld.components)}")
    print(f"   🔗 Connections: {len(sld.connections)}")
    print(f"   ⚡ Voltage levels: {sld.voltage_levels}")
    print(f"   ⏱️  Processing time: {sld.metadata.get('processing_time_ms', 0)}ms")
    
    if sld.components:
        print(f"\n🎯 First 3 components:")
        for i, comp in enumerate(sld.components[:3]):
            print(f"   {i+1}. {comp.component_type.value} @ ({comp.position.x:.0f}, {comp.position.y:.0f}) - Confidence: {comp.confidence:.2f}")
    else:
        print(f"ℹ️  No components detected in random test image (expected)")
        
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

