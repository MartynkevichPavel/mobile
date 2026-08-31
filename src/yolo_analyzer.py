import os
import numpy as np
from PIL import Image
import tflite_runtime.interpreter as tflite
from src.config import CONF_THRESHOLD, INPUT_SIZE, COCO_CLASSES, IOU_THRESHOLD


class YOLOAnalyzer:
    def __init__(self, model_path: str):
        self.model_path = model_path
        self.interpreter = None
        self.input_details = None
        self.output_details = None
        self._load_model()

    def _load_model(self):
        try:
            # Проверяем, что файл существует
            if not os.path.exists(self.model_path):
                raise FileNotFoundError(f"Модель не найдена: {self.model_path}")
        
            # Загружаем модель с явными настройками для мобильных устройств
            self.interpreter = tflite.Interpreter(
                model_path=self.model_path,
                num_threads=2  # Ограничиваем потоки для мобильных устройств
            )
            self.interpreter.allocate_tensors()
            self.input_details = self.interpreter.get_input_details()
            self.output_details = self.interpreter.get_output_details()
        
            print(f"✅ Модель загружена: {self.model_path}")
            print(f"   Вход: {self.input_details[0]['shape']}")
            print(f"   Входной тип: {self.input_details[0]['dtype']}")
            print(f"   Выход: {self.output_details[0]['shape']}")
            print(f"   Выходной тип: {self.output_details[0]['dtype']}")
        
        except Exception as e:
            print(f"❌ Ошибка загрузки модели: {e}")
            raise

    def analyze(self, image_path: str, conf_threshold: float = CONF_THRESHOLD):
        try:
            # 1. Проверяем файл
            if not os.path.exists(image_path):
                print(f"❌ Файл не найден: {image_path}")
                return []
            
            # 2. Загружаем изображение
            img = Image.open(image_path).convert('RGB')
            original_size = img.size
            print(f"\n📸 Анализ: {os.path.basename(image_path)} ({original_size[0]}x{original_size[1]})")
            
            # 3. Изменяем размер
            img_resized = img.resize((INPUT_SIZE, INPUT_SIZE))
            
            # 4. Преобразуем в numpy array (FLOAT32!)
            input_data = np.array(img_resized, dtype=np.float32)
            
            # 5. Нормализуем (делим на 255.0)
            input_data = input_data / 255.0
            
            # 6. Добавляем размерность батча
            input_data = np.expand_dims(input_data, axis=0)
            
            # 7. Выполняем инференс
            self.interpreter.set_tensor(self.input_details[0]['index'], input_data)
            self.interpreter.invoke()

            # 8. Получаем результаты
            output_data = self.interpreter.get_tensor(self.output_details[0]['index'])
            
            # 9. Постобработка
            detections = self._postprocess(output_data, conf_threshold)
            
            print(f"   Найдено объектов: {len(detections)}")
            
            # 10. Если объектов нет - пробуем с пониженным порогом
            if len(detections) == 0 and conf_threshold > 0.05:
                print(f"   🔄 Повторный анализ с порогом 0.05")
                detections = self._postprocess(output_data, 0.05)
                print(f"   Найдено объектов (порог 0.05): {len(detections)}")
            
            # 11. Показываем первые 5 детекций
            if detections:
                for i, det in enumerate(detections[:5]):
                    print(f"   {i+1}. {det['class']} ({det['confidence']:.3f}) bbox={det['bbox']}")
            
            return detections

        except Exception as e:
            print(f"❌ Ошибка анализа: {e}")
            import traceback
            traceback.print_exc()
            return []

    def _postprocess(self, output_data, conf_threshold):
        detections = []
        output = output_data[0]
        
        # Получаем максимальную уверенность
        max_conf = np.max(output[4:, :])
        print(f"   Максимальная уверенность: {max_conf:.4f}")
        
        # Если максимальная уверенность ниже порога - модель ничего не нашла
        if max_conf < conf_threshold:
            print(f"   ⚠️ Максимальная уверенность ({max_conf:.4f}) ниже порога ({conf_threshold})")
            return []
        
        # YOLO output: [84, 8400] или [84, 2100]
        for i in range(output.shape[1]):
            scores = output[4:, i]
            class_id = np.argmax(scores)
            confidence = scores[class_id]

            if confidence > conf_threshold:
                x_center = output[0, i]
                y_center = output[1, i]
                width = output[2, i]
                height = output[3, i]

                # Преобразуем координаты в пиксели
                x1 = int((x_center - width / 2) * INPUT_SIZE)
                y1 = int((y_center - height / 2) * INPUT_SIZE)
                x2 = int((x_center + width / 2) * INPUT_SIZE)
                y2 = int((y_center + height / 2) * INPUT_SIZE)

                # Проверяем корректность координат
                if x1 >= x2 or y1 >= y2:
                    continue

                class_name = COCO_CLASSES[class_id] if class_id < len(COCO_CLASSES) else f'class_{class_id}'

                detections.append({
                    'class': class_name,
                    'confidence': float(confidence),
                    'bbox': [x1, y1, x2, y2],
                    'class_id': int(class_id)
                })

        # Сортируем по уверенности
        detections.sort(key=lambda x: x['confidence'], reverse=True)

        # NMS (Non-Maximum Suppression) - удаляем дублирующиеся рамки
        filtered = []
        for det in detections:
            keep = True
            for f in filtered:
                if self._calculate_iou(det['bbox'], f['bbox']) > IOU_THRESHOLD:
                    keep = False
                    break
            if keep:
                filtered.append(det)

        return filtered

    def _calculate_iou(self, box1, box2):
        """IoU (Intersection over Union) для двух боксов"""
        x1 = max(box1[0], box2[0])
        y1 = max(box1[1], box2[1])
        x2 = min(box1[2], box2[2])
        y2 = min(box1[3], box2[3])

        intersection = max(0, x2 - x1) * max(0, y2 - y1)
        area1 = (box1[2] - box1[0]) * (box1[3] - box1[1])
        area2 = (box2[2] - box2[0]) * (box2[3] - box2[1])
        union = area1 + area2 - intersection

        return intersection / union if union > 0 else 0

    def analyze_batch(self, image_paths: list, conf_threshold: float = CONF_THRESHOLD):
        """Анализирует несколько изображений"""
        results = []
        for path in image_paths:
            detections = self.analyze(path, conf_threshold)
            results.append({
                'path': path,
                'detections': detections,
                'count': len(detections)
            })
        return results
    
    def get_model_info(self):
        """Возвращает информацию о модели"""
        return {
            'model_path': self.model_path,
            'input_shape': self.input_details[0]['shape'] if self.input_details else None,
            'input_dtype': self.input_details[0]['dtype'] if self.input_details else None,
            'output_shape': self.output_details[0]['shape'] if self.output_details else None,
            'output_dtype': self.output_details[0]['dtype'] if self.output_details else None,
        }