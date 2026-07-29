#!/usr/bin/env python3
"""
Тестовый скрипт для проверки модели YOLO на изображении
"""

import os
import sys

# Добавляем путь к src
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.config import MODEL_PATH, CONF_THRESHOLD
from src.yolo_analyzer import YOLOAnalyzer


def main():
    # Проверяем модель
    if not os.path.exists(MODEL_PATH):
        print(f"❌ Модель не найдена: {MODEL_PATH}")
        return
    
    # Создаем анализатор
    analyzer = YOLOAnalyzer(MODEL_PATH)
    
    # Путь к тестовому изображению
    test_image = "test_bus.jpg"
    
    if not os.path.exists(test_image):
        print(f"❌ Изображение не найдено: {test_image}")
        print("Скачайте тестовое изображение:")
        print("  wget https://github.com/ultralytics/assets/raw/main/images/bus.jpg")
        return
    
    # Анализируем
    print("\n" + "="*50)
    print("🔍 АНАЛИЗ ИЗОБРАЖЕНИЯ")
    print("="*50)
    
    detections = analyzer.analyze(test_image, conf_threshold=CONF_THRESHOLD)
    
    print("\n" + "="*50)
    print(f"📊 РЕЗУЛЬТАТ: найдено {len(detections)} объектов")
    print("="*50)
    
    for i, det in enumerate(detections):
        print(f"{i+1}. {det['class']}: {det['confidence']:.3f}")
        print(f"   bbox: {det['bbox']}")


if __name__ == "__main__":
    main()