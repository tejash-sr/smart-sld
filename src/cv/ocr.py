"""OCR module - PaddleOCR with Tesseract fallback."""
from __future__ import annotations
from dataclasses import dataclass, field
import cv2
import numpy as np
from PIL import Image

@dataclass
class TextExtraction:
    text: str
    confidence: float
    bbox: tuple[int, int, int, int]  # x, y, w, h
    angle: float = 0.0

class TextExtractor:
    """PaddleOCR primary, Tesseract fallback for text extraction.

    Gracefully degrades when engines unavailable. In production,
    ensure at least one OCR engine is installed.
    """

    def __init__(self, engine: str = "auto"):
        self.engine_name = engine
        self._paddle = None
        self._tesseract_available = self._check_tesseract()

        if engine == "auto":
            self.engine = self._select_best_engine()
        else:
            self.engine = engine

        self._init_engine()

    def _check_tesseract(self) -> bool:
        import subprocess
        try:
            result = subprocess.run(
                ["tesseract", "--version"],
                capture_output=True, text=True, timeout=5
            )
            return result.returncode == 0
        except Exception:
            return False

    def _select_best_engine(self) -> str:
        if self._check_paddle_available():
            return "paddle"
        elif self._tesseract_available:
            return "tesseract"
        return "fallback"

    def _check_paddle_available(self) -> bool:
        try:
            import paddle
            import paddleocr
            return True
        except Exception:
            return False

    def _init_engine(self) -> None:
        if self.engine == "paddle":
            try:
                from paddleocr import PaddleOCR
                self._paddle = PaddleOCR(
                    lang="en", use_angle_cls=True,
                    show_log=False
                )
            except Exception as e:
                self.engine = "tesseract" if self._tesseract_available else "fallback"
                self._init_engine()
        elif self.engine == "tesseract":
            import pytesseract
            self._tesseract = pytesseract

    def extract_all_text(self, image: np.ndarray) -> list[TextExtraction]:
        if self.engine == "fallback":
            return []
        try:
            if self.engine == "paddle" and self._paddle:
                return self._extract_paddle(image)
            elif self.engine == "tesseract":
                return self._extract_tesseract(image)
        except Exception:
            return []
        return []

    def _extract_paddle(self, image: np.ndarray) -> list[TextExtraction]:
        results = self._paddle.ocr(image, cls=True)
        extractions = []
        if not results or not results[0]:
            return []
        for line in results[0]:
            if not line:
                continue
            box = line[0]
            text = line[1][0]
            conf = float(line[1][1])
            x_coords = [p[0] for p in box]
            y_coords = [p[1] for p in box]
            x, y = int(min(x_coords)), int(min(y_coords))
            w, h = int(max(x_coords) - x), int(max(y_coords) - y)
            angle = 0.0
            try:
                angle = float(line[1][2].get("angle", 0))
            except Exception:
                pass
            extractions.append(TextExtraction(text=text, confidence=conf, bbox=(x, y, w, h), angle=angle))
        return extractions

    def _extract_tesseract(self, image: np.ndarray) -> list[TextExtraction]:
        import pytesseract
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        data = pytesseract.image_to_data(gray, output_type=pytesseract.Output.DICT)
        extractions = []
        n_boxes = len(data["text"])
        for i in range(n_boxes):
            text = data["text"][i].strip()
            if not text:
                continue
            conf = float(data["conf"][i])
            if conf < 30:
                continue
            x, y, w, h = data["left"][i], data["top"][i], data["width"][i], data["height"][i]
            extractions.append(TextExtraction(text=text, confidence=conf / 100.0, bbox=(x, y, w, h)))
        return extractions

    def extract_region(self, image: np.ndarray, bbox: tuple[int, int, int, int]) -> TextExtraction | None:
        x, y, w, h = bbox
        region = image[y:y+h, x:x+w] if len(image.shape) == 2 else image[y:y+h, x:x+w]
        results = self.extract_all_text(region)
        if not results:
            return None
        return max(results, key=lambda r: r.confidence)
