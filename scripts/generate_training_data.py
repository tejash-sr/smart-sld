"""Generate synthetic SLD images for YOLO training"""
import cv2
import numpy as np
import json
from pathlib import Path
from datetime import datetime
import random
from enum import Enum

class ComponentType(Enum):
    """Electrical component types"""
    CIRCUIT_BREAKER = 0
    DISCONNECT_SWITCH = 1
    TRANSFORMER_2W = 2
    BUSBAR = 3
    CURRENT_TRANSFORMER = 4
    VOLTAGE_TRANSFORMER = 5
    REACTOR = 6
    CAPACITOR = 7
    GENERATOR = 8
    FEEDER_TERMINAL = 9
    GROUND = 10
    SURGE_ARRESTER = 11
    FUSE = 12
    LOAD_BREAK_SWITCH = 13


def draw_circuit_breaker(img, center, size, angle=0):
    """Draw circuit breaker symbol"""
    x, y = center
    pts = np.array([
        [-size, -size*0.3],
        [-size*0.3, -size],
        [size*0.3, size],
        [size, size*0.3]
    ])
    
    cos_a, sin_a = np.cos(angle), np.sin(angle)
    rot = np.array([[cos_a, -sin_a], [sin_a, cos_a]])
    pts = (pts @ rot.T).astype(int) + center
    cv2.polylines(img, [pts], False, (255, 100, 0), 2)


def draw_transformer(img, center, size, angle=0):
    """Draw transformer symbol (two coils)"""
    x, y = center
    # Left coil
    cv2.circle(img, (int(x - size*0.4), int(y)), int(size*0.4), (0, 200, 255), 2)
    # Right coil
    cv2.circle(img, (int(x + size*0.4), int(y)), int(size*0.4), (0, 200, 255), 2)


def draw_busbar(img, center, size, angle=0):
    """Draw busbar (thick horizontal line)"""
    x, y = center
    cos_a, sin_a = np.cos(angle), np.sin(angle)
    
    p1 = (int(x - size*0.8*cos_a), int(y - size*0.8*sin_a))
    p2 = (int(x + size*0.8*cos_a), int(y + size*0.8*sin_a))
    cv2.line(img, p1, p2, (0, 255, 0), 4)


def draw_ground(img, center, size, angle=0):
    """Draw ground symbol"""
    x, y = center
    # Vertical line
    cv2.line(img, (int(x), int(y - size)), (int(x), int(y + size)), (100, 100, 255), 2)
    # Horizontal lines
    for i in range(3):
        line_len = size * (1 - i*0.3)
        y_pos = int(y + size*0.3 + i*size*0.3)
        cv2.line(img, (int(x - line_len), y_pos), (int(x + line_len), y_pos), (100, 100, 255), 2)


def draw_capacitor(img, center, size, angle=0):
    """Draw capacitor symbol (two plates)"""
    x, y = center
    cos_a, sin_a = np.cos(angle), np.sin(angle)
    
    # Top plate
    p1 = (int(x - size*0.6*cos_a - size*0.3*sin_a), int(y - size*0.6*sin_a + size*0.3*cos_a))
    p2 = (int(x - size*0.6*cos_a + size*0.3*sin_a), int(y - size*0.6*sin_a - size*0.3*cos_a))
    cv2.line(img, p1, p2, (255, 0, 255), 3)
    
    # Bottom plate
    p3 = (int(x + size*0.6*cos_a - size*0.3*sin_a), int(y + size*0.6*sin_a + size*0.3*cos_a))
    p4 = (int(x + size*0.6*cos_a + size*0.3*sin_a), int(y + size*0.6*sin_a - size*0.3*cos_a))
    cv2.line(img, p3, p4, (255, 0, 255), 3)


def draw_generator(img, center, size, angle=0):
    """Draw generator symbol (circle with G)"""
    x, y = center
    cv2.circle(img, (int(x), int(y)), int(size), (200, 200, 0), 2)
    cv2.putText(img, 'G', (int(x - size*0.2), int(y + size*0.2)), 
                cv2.FONT_HERSHEY_SIMPLEX, size*0.01, (200, 200, 0), 1)


def draw_component(img, comp_type, center, size=30, angle=0):
    """Draw component based on type"""
    if comp_type == ComponentType.CIRCUIT_BREAKER:
        draw_circuit_breaker(img, center, size, angle)
    elif comp_type == ComponentType.TRANSFORMER_2W:
        draw_transformer(img, center, size, angle)
    elif comp_type == ComponentType.BUSBAR:
        draw_busbar(img, center, size, angle)
    elif comp_type == ComponentType.GROUND:
        draw_ground(img, center, size, angle)
    elif comp_type == ComponentType.CAPACITOR:
        draw_capacitor(img, center, size, angle)
    elif comp_type == ComponentType.GENERATOR:
        draw_generator(img, center, size, angle)
    else:
        # Generic symbol for other types
        cv2.circle(img, center, int(size*0.5), (150, 150, 255), 2)


def generate_sld_image(width=640, height=480, num_components=8, num_connections=5):
    """Generate a synthetic SLD diagram image"""
    # Create image with white background
    img = np.ones((height, width, 3), dtype=np.uint8) * 255
    
    # Add subtle noise
    noise = np.random.normal(0, 3, img.shape).astype(np.uint8)
    img = cv2.add(img, noise)
    
    # Generate random components
    components = []
    positions = []
    
    for i in range(num_components):
        # Random position avoiding edges
        x = np.random.randint(80, width - 80)
        y = np.random.randint(60, height - 60)
        
        # Check minimum distance from other components
        too_close = False
        for px, py in positions:
            if ((x - px)**2 + (y - py)**2) ** 0.5 < 80:
                too_close = True
                break
        
        if too_close:
            continue
        
        comp_type = random.choice(list(ComponentType))
        size = np.random.randint(15, 35)
        angle = np.random.uniform(0, np.pi * 2)
        
        draw_component(img, comp_type, (x, y), size, angle)
        
        components.append({
            "type": comp_type.name.lower(),
            "type_id": comp_type.value,
            "x": x,
            "y": y,
            "size": size,
            "angle": angle,
        })
        positions.append((x, y))
    
    # Draw random connections between nearby components
    for _ in range(min(num_connections, len(components)-1)):
        if len(components) < 2:
            break
        idx1, idx2 = random.sample(range(len(components)), 2)
        x1, y1 = components[idx1]["x"], components[idx1]["y"]
        x2, y2 = components[idx2]["x"], components[idx2]["y"]
        cv2.line(img, (x1, y1), (x2, y2), (150, 150, 150), 1)
    
    # Add voltage markers
    cv2.putText(img, '220kV', (20, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 1)
    cv2.putText(img, '110kV', (20, height - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 1)
    
    return img, components


def create_yolo_annotations(components, img_width, img_height):
    """Create YOLO format annotation (normalized bounding boxes)"""
    annotations = []
    for comp in components:
        x_center = comp["x"] / img_width
        y_center = comp["y"] / img_height
        width = (comp["size"] * 2) / img_width
        height = (comp["size"] * 2) / img_height
        
        # YOLO format: class_id x_center y_center width height (normalized)
        annotations.append(f"{comp['type_id']} {x_center:.6f} {y_center:.6f} {width:.6f} {height:.6f}")
    
    return "\n".join(annotations)


def generate_training_dataset(output_dir="data/training", num_images=100, img_width=640, img_height=480):
    """Generate complete YOLO training dataset"""
    output_path = Path(output_dir)
    images_dir = output_path / "images"
    labels_dir = output_path / "labels"
    
    # Create directories
    images_dir.mkdir(parents=True, exist_ok=True)
    labels_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"🎨 Generating {num_images} synthetic SLD images...")
    
    for i in range(num_images):
        # Generate image
        img, components = generate_sld_image(
            width=img_width,
            height=img_height,
            num_components=np.random.randint(5, 15),
            num_connections=np.random.randint(3, 8)
        )
        
        # Save image
        img_name = f"sld_synthetic_{i:04d}.jpg"
        img_path = images_dir / img_name
        cv2.imwrite(str(img_path), img)
        
        # Save YOLO annotations
        annotations = create_yolo_annotations(components, img_width, img_height)
        label_name = f"sld_synthetic_{i:04d}.txt"
        label_path = labels_dir / label_name
        label_path.write_text(annotations)
        
        if (i + 1) % 10 == 0:
            print(f"  ✅ Generated {i + 1}/{num_images} images")
    
    # Create YOLO dataset config (data.yaml)
    num_train = int(num_images * 0.8)
    num_val = num_images - num_train
    
    data_yaml = f"""path: {output_path.absolute()}
train: images
val: images

nc: {len(ComponentType)}
names: [{', '.join([f"'{c.name.lower()}'" for c in ComponentType])}]
"""
    
    (output_path / "data.yaml").write_text(data_yaml)
    
    print(f"\n✅ Training dataset created!")
    print(f"   📁 Images: {images_dir}")
    print(f"   📁 Labels: {labels_dir}")
    print(f"   📊 Total: {num_images} images ({num_train} train, {num_val} val)")
    print(f"   📝 Config: {output_path / 'data.yaml'}")
    
    return output_path


if __name__ == "__main__":
    # Generate training dataset
    dataset_path = generate_training_dataset(
        output_dir="data/training",
        num_images=300,  # Start with 300 synthetic images
        img_width=640,
        img_height=480
    )
    
    print("\n🚀 Next steps:")
    print(f"1. Train YOLO: python scripts/train_yolo.py --data-dir {dataset_path}")
    print("2. Model will be saved to: models/sld_detector.pt")
