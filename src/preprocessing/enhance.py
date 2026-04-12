"""Image preprocessing pipeline for SLD enhancement."""
from __future__ import annotations
import cv2
import numpy as np
from PIL import Image

class SLDPreprocessor:
    TARGET_DPI = 200

    def __init__(self, target_dpi: int = TARGET_DPI):
        self.target_dpi = target_dpi

    def preprocess(self, image: np.ndarray) -> np.ndarray:
        """Full preprocessing pipeline."""
        img = self._to_grayscale(image)
        img = self._deskew(img)
        img = self._remove_noise(img)
        img = self._normalize_contrast(img)
        img = self._binarize(img)
        return img

    def _to_grayscale(self, image: np.ndarray) -> np.ndarray:
        if len(image.shape) == 3:
            return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        return image

    def _deskew(self, image: np.ndarray) -> np.ndarray:
        coords = np.column_stack(np.where(image > 0))
        if len(coords) == 0:
            return image
        angle = cv2.minAreaRect(coords)[-1]
        if angle < -45:
            angle = -(90 + angle)
        else:
            angle = -angle
        if abs(angle) < 0.5:
            return image
        h, w = image.shape
        M = cv2.getRotationMatrix2D((w // 2, h // 2), angle, 1.0)
        return cv2.warpAffine(image, M, (w, h), flags=cv2.INTER_CUBIC, borderValue=255)

    def _remove_noise(self, image: np.ndarray) -> np.ndarray:
        return cv2.medianBlur(image, 3)

    def _normalize_contrast(self, image: np.ndarray) -> np.ndarray:
        return cv2.equalizeHist(image)

    def _binarize(self, image: np.ndarray) -> np.ndarray:
        return cv2.adaptiveThreshold(
            image, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV, 21, 10
        )

    @staticmethod
    def load_image(path: str) -> np.ndarray:
        pil = Image.open(path)
        if pil.mode != "RGB":
            pil = pil.convert("RGB")
        return cv2.cvtColor(np.array(pil), cv2.COLOR_RGB2BGR)
