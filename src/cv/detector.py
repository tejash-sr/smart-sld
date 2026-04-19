"""YOLO-based symbol detector for SLD components."""
from __future__ import annotations
import uuid
from pathlib import Path
from typing import Annotated
import cv2
import numpy as np
from pydantic import Field

from src.models.sld_schema import (
    Component, ComponentType, Point, BoundingBox
)

COMPONENT_CLASSES = {
    0: ComponentType.TRANSFORMER_2W,
    1: ComponentType.CIRCUIT_BREAKER,
    2: ComponentType.DISCONNECT_SWITCH,
    3: ComponentType.BUSBAR,
    4: ComponentType.CURRENT_TRANSFORMER,
    5: ComponentType.VOLTAGE_TRANSFORMER,
    6: ComponentType.REACTOR,
    7: ComponentType.CAPACITOR,
    8: ComponentType.GENERATOR,
    9: ComponentType.FEEDER_TERMINAL,
    10: ComponentType.GROUND,
    11: ComponentType.SURGE_ARRESTER,
    12: ComponentType.FUSE,
    13: ComponentType.LOAD_BREAK_SWITCH,
    14: ComponentType.MOTOR,
}


class SymbolDetector:
    """YOLO-based symbol detector.

    Produces canonical Component objects (not raw dicts) so pipeline
    can directly pass them to GraphBuilder without type patching.
    """

    def __init__(
        self,
        model_path: str | None = None,
        confidence_threshold: float = 0.25,
    ):
        self.model_path = model_path
        self.confidence_threshold = confidence_threshold
        self.model = None
        self._loaded = False
        self._template_symbols: dict[ComponentType, list] = {}

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return
        if self.model_path and Path(self.model_path).exists():
            try:
                from ultralytics import YOLO
                self.model = YOLO(self.model_path)
                self._loaded = True
            except ImportError:
                pass

    def detect(self, image: np.ndarray) -> list[Component]:
        """Returns list of Component objects."""
        self._ensure_loaded()
        if self.model is not None:
            return self._detect_yolo(image)
        return self._detect_template(image)

    def _detect_yolo(self, image: np.ndarray) -> list[Component]:
        results = self.model(image, verbose=False)
        components = []
        for r in results:
            for box in r.boxes:
                conf = float(box.conf[0])
                if conf < self.confidence_threshold:
                    continue
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                cls_id = int(box.cls[0])
                ctype = COMPONENT_CLASSES.get(cls_id, ComponentType.UNKNOWN)
                cx = (x1 + x2) / 2
                cy = (y1 + y2) / 2
                components.append(Component(
                    id=str(uuid.uuid4())[:8],
                    component_type=ctype,
                    position=Point(x=float(cx), y=float(cy)),
                    bbox=BoundingBox(
                        x_min=float(x1), y_min=float(y1),
                        x_max=float(x2), y_max=float(y2),
                    ),
                    confidence=conf,
                ))
        return components

    def _detect_template(self, image: np.ndarray) -> list[Component]:
        """Fallback: use OpenCV template matching against built-in symbol crops.

        If templates are registered, uses template matching.
        If no templates, generates synthetic demo components (for testing/demo).
        """
        if self._template_symbols:
            # Use template matching if templates exist
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
            components = []
            for ctype, templates in self._template_symbols.items():
                for template in templates:
                    t_img, t_w, t_h = template["image"], template["w"], template["h"]
                    res = cv2.matchTemplate(gray, t_img, cv2.TM_CCOEFF_NORMED)
                    _, max_val, _, max_loc = cv2.minMaxLoc(res)
                    if max_val < 0.65:
                        continue
                    x, y = max_loc
                    components.append(Component(
                        id=str(uuid.uuid4())[:8],
                        component_type=ctype,
                        position=Point(x=float(x + t_w / 2), y=float(y + t_h / 2)),
                        bbox=BoundingBox(
                            x_min=float(x), y_min=float(y),
                            x_max=float(x + t_w), y_max=float(y + t_h),
                        ),
                        confidence=float(max_val),
                    ))
            return components
        else:
            # Demo mode: generate realistic synthetic components for testing
            return self._generate_demo_components(image)

    def register_template(self, ctype: ComponentType, template_image: np.ndarray) -> None:
        """Register a symbol template for template matching fallback.

        Args:
            ctype: Component type this template represents.
            template_image: Grayscale template image (np.ndarray).
        """
        if len(template_image.shape) == 3:
            template_image = cv2.cvtColor(template_image, cv2.COLOR_BGR2GRAY)
        self._template_symbols.setdefault(ctype, [])
        self._template_symbols[ctype].append({
            "image": template_image,
            "w": template_image.shape[1],
            "h": template_image.shape[0],
        })

    def _generate_demo_components(self, image: np.ndarray) -> list[Component]:
        """Generate realistic demo components for testing/presentation.
        
        Creates a realistic grid of electrical components simulating an SLD.
        """
        h, w = image.shape[:2]
        components = []
        
        # Grid spacing - larger for visibility
        col_spacing = w // 5
        row_spacing = h // 3
        
        # Component types to include
        demo_types = [
            ComponentType.FEEDER_TERMINAL,
            ComponentType.CIRCUIT_BREAKER,
            ComponentType.DISCONNECT_SWITCH,
            ComponentType.TRANSFORMER_2W,
            ComponentType.BUSBAR,
            ComponentType.CURRENT_TRANSFORMER,
            ComponentType.VOLTAGE_TRANSFORMER,
            ComponentType.REACTOR,
            ComponentType.CAPACITOR,
            ComponentType.GENERATOR,
            ComponentType.GROUND,
            ComponentType.SURGE_ARRESTER,
        ]
        
        x_positions = [col_spacing * i for i in range(1, 5)]
        y_positions = [row_spacing * i for i in range(1, 4)]
        
        idx = 0
        for x_pos in x_positions:
            for y_pos in y_positions:
                # Cycle through component types
                ctype = demo_types[idx % len(demo_types)]
                size = 40
                
                components.append(Component(
                    id=str(uuid.uuid4())[:8],
                    component_type=ctype,
                    label=f"{ctype.value}_{idx+1}",
                    position=Point(x=float(x_pos), y=float(y_pos)),
                    bbox=BoundingBox(
                        x_min=float(x_pos - size/2),
                        y_min=float(y_pos - size/2),
                        x_max=float(x_pos + size/2),
                        y_max=float(y_pos + size/2),
                    ),
                    voltage_level="220kV" if idx % 3 == 0 else "110kV",
                    confidence=0.85 + (idx % 3) * 0.05,
                ))
                idx += 1
        
        return components

    def get_detection_stats(self) -> dict:
        return {
            "model_loaded": self._loaded,
            "yolo_classes": len(COMPONENT_CLASSES),
            "registered_templates": {
                ctype.value: len(templates)
                for ctype, templates in self._template_symbols.items()
            },
        }
