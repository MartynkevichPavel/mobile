import numpy as np
from PIL import Image
import tflite_runtime.interpreter as tflite
from config import CONF_THRESHOLD, INPUT_SIZE, COCO_CLASSES, IOU_THRESHOLD


class YOLOAnalyzer:
    def __init__(self, model_path: str):
        self.model_path = model_path
        self.interpreter = None
        self.input_details = None
        self.output_details = None
        self._load_model()

    def _load_model(self):
        try:
            self.interpreter = tflite.Interpreter(model_path=self.model_path)
            self.interpreter.allocate_tensors()
            self.input_details = self.interpreter.get_input_details()
            self.output_details = self.interpreter.get_output_details()
            print(f"✅ Модель загружена: {self.model_path}")
            print(f"   Вход: {self.input_details[0]['shape']}")
            print(f"   Выход: {self.output_details[0]['shape']}")
        except Exception as e:
            print(f"❌ Ошибка загрузки модели: {e}")
            raise

    def analyze(self, image_path: str, conf_threshold: float = CONF_THRESHOLD):
        try:
            img = Image.open(image_path).convert('RGB')
            img_resized = img.resize((INPUT_SIZE, INPUT_SIZE))
            
            # 1. Преобразуем в numpy array (FLOAT32!)
            input_data = np.array(img_resized, dtype=np.float32)
            
            # 2. Нормализуем (делим на 255.0)
            input_data = input_data / 255.0
            
            # 3. Добавляем размерность батча
            input_data = np.expand_dims(input_data, axis=0)
            
            # 4. Выполняем инференс
            self.interpreter.set_tensor(self.input_details[0]['index'], input_data)
            self.interpreter.invoke()

            output_data = self.interpreter.get_tensor(self.output_details[0]['index'])
            return self._postprocess(output_data, conf_threshold)

        except Exception as e:
            print(f"❌ Ошибка анализа: {e}")
            return []

    def _postprocess(self, output_data, conf_threshold):
        detections = []
        output = output_data[0]
        for i in range(output.shape[1]):
            scores = output[4:, i]
            class_id = np.argmax(scores)
            confidence = scores[class_id]

            if confidence > conf_threshold:
                x_center = output[0, i]
                y_center = output[1, i]
                width = output[2, i]
                height = output[3, i]

                x1 = int((x_center - width / 2) * INPUT_SIZE)
                y1 = int((y_center - height / 2) * INPUT_SIZE)
                x2 = int((x_center + width / 2) * INPUT_SIZE)
                y2 = int((y_center + height / 2) * INPUT_SIZE)

                detections.append({
                    'class': COCO_CLASSES[class_id] if class_id < len(COCO_CLASSES) else f'class_{class_id}',
                    'confidence': float(confidence),
                    'bbox': [x1, y1, x2, y2],
                    'class_id': int(class_id)
                })

        detections.sort(key=lambda x: x['confidence'], reverse=True)

        # NMS
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
        x1 = max(box1[0], box2[0])
        y1 = max(box1[1], box2[1])
        x2 = min(box1[2], box2[2])
        y2 = min(box1[3], box2[3])

        intersection = max(0, x2 - x1) * max(0, y2 - y1)
        area1 = (box1[2] - box1[0]) * (box1[3] - box1[1])
        area2 = (box2[2] - box2[0]) * (box2[3] - box2[1])
        union = area1 + area2 - intersection

        return intersection / union if union > 0 else 0