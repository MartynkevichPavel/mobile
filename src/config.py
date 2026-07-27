import os
import sys

# ===== БАЗОВЫЙ ПУТЬ =====
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ===== ПУТИ =====
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
MODEL_PATH = os.path.join(ASSETS_DIR, "vehicle-detector-yolov8n-int8.tflite")
DB_PATH = os.path.join(BASE_DIR, "photo_db")

# ===== НАСТРОЙКИ YOLO =====
CONF_THRESHOLD = 0.3
IOU_THRESHOLD = 0.5
INPUT_SIZE = 320

# ===== КЛАССЫ COCO =====
COCO_CLASSES = [
    'person', 'bicycle', 'car', 'motorcycle', 'airplane', 'bus', 'truck', 'boat',
    'traffic light', 'fire hydrant', 'stop sign', 'parking meter', 'bench',
    'bird', 'cat', 'dog', 'horse', 'sheep', 'cow', 'elephant', 'bear',
    'zebra', 'giraffe', 'backpack', 'umbrella', 'handbag', 'tie', 'suitcase',
    'frisbee', 'skis', 'snowboard', 'sports ball', 'kite', 'baseball bat',
    'baseball glove', 'skateboard', 'surfboard', 'tennis racket',
    'bottle', 'wine glass', 'cup', 'fork', 'knife', 'spoon', 'bowl',
    'banana', 'apple', 'sandwich', 'orange', 'broccoli', 'carrot', 'hot dog',
    'pizza', 'donut', 'cake', 'chair', 'couch', 'potted plant', 'bed',
    'dining table', 'toilet', 'tv', 'laptop', 'mouse', 'remote', 'keyboard',
    'cell phone', 'microwave', 'oven', 'toaster', 'sink', 'refrigerator',
    'book', 'clock', 'vase', 'scissors', 'teddy bear', 'hair drier', 'toothbrush'
]

print(f"🔍 Путь к модели: {MODEL_PATH}")
print(f"📁 Файл существует: {os.path.exists(MODEL_PATH)}")