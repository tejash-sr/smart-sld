"""FastAPI application for SLD interpretation service."""
from __future__ import annotations
import uuid
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
import numpy as np
import cv2

from src.pipeline import SLDPipeline
from src.models.sld_schema import ExtractedSLD

app = FastAPI(title="SLD Interpretation API", version="0.1.0")
pipeline: SLDPipeline | None = None

@app.on_event("startup")
def startup():
    global pipeline
    pipeline = SLDPipeline()

@app.post("/interpret")
async def interpret_sld(file: UploadFile = File(...)) -> JSONResponse:
    """Accept SLD image/PDF, return structured JSON."""
    if pipeline is None:
        raise HTTPException(503, "Pipeline not initialized")
    
    contents = await file.read()
    nparr = np.frombuffer(contents, np.uint8)
    image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    if image is None:
        raise HTTPException(400, "Cannot decode image")
    
    sld = pipeline.process_image_array(image, source_filename=file.filename)
    return JSONResponse(content=sld.to_dict())

@app.get("/health")
def health():
    return {"status": "ok", "pipeline": pipeline is not None}

@app.get("/model-stats")
def model_stats():
    if pipeline is None:
        return {"error": "pipeline not initialized"}
    return pipeline.detector.get_detection_stats()
