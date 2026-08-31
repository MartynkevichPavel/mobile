import os
from datetime import datetime
from typing import List, Dict, Optional
from src.config import DB_PATH

class GalleryScanner:
    """Класс для быстрого поиска изображений в галерее."""
    
    # Поддерживаемые расширения изображений
    IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.bmp', '.gif', '.webp'}
    
    # Стандартные папки с изображениямиs
    PHOTO_DIRS = [
        'DCIM',           # Камера
        'Pictures',       # Картинки
        'Photos',         # Фото
        'Camera',         # Камера
        'Screenshots',    # Скриншоты
        'Download',       # Загрузки
        'WhatsApp/Media/WhatsApp Images',  # WhatsApp
        'Instagram',      # Instagram
        'Telegram/Telegram Images',        # Telegram
        'Snapchat',       # Snapchat
    ]

    def __init__(self):
        self.photos = []

    def find_photos(self, base_path: str = None) -> List[Dict]:
        """
        Быстрый поиск изображений в стандартных папках.
        
        Args:
            base_path: Базовый путь для поиска (если None - определяется автоматически)
        
        Returns:
            List[Dict]: Список найденных изображений с метаданными
        """
        self.photos = []
        
        # Определяем базовый путь
        if base_path is None:
            base_path = self._get_default_base_path()
        
        if not base_path:
            print("❌ Не удалось определить путь к галерее")
            return []
        
        print(f"📁 Поиск фото в: {base_path}")
        
        # Ищем в каждой папке
        for dir_name in self.PHOTO_DIRS:
            dir_path = os.path.join(base_path, dir_name)
            if os.path.exists(dir_path):
                self._scan_directory(dir_path)
        
        print(f"✅ Найдено изображений: {len(self.photos)}")
        return self.photos

    def _get_default_base_path(self) -> Optional[str]:
        """
        Определяет стандартный путь к галерее на устройстве.
        
        Returns:
            Optional[str]: Путь к корневой папке с медиа
        """
        home = os.path.expanduser("~")
        
        # Пути для разных платформ
        paths_to_check = [
            # Android (включая эмуляторы и реальные устройства)
            "/storage/emulated/0",
            "/sdcard",
            "/mnt/sdcard",
            os.path.join(home, "storage", "emulated", "0"),
            # Linux/Windows WSL
            os.path.join(home, "Pictures"),
            os.path.join(home, "Photos"),
            os.path.join(home, "DCIM"),
            os.path.join(home, "Downloads"),
            os.path.join(home, "Desktop"),
            # Windows
            os.path.join(os.environ.get("USERPROFILE", ""), "Pictures"),
            os.path.join(os.environ.get("USERPROFILE", ""), "Downloads"),
            os.path.join(os.environ.get("USERPROFILE", ""), "Desktop"),
            os.path.join(os.environ.get("USERPROFILE", ""), "OneDrive", "Pictures"),
            # Mac
            os.path.join(home, "Pictures"),
            os.path.join(home, "Downloads"),
        ]
        
        for path in paths_to_check:
            if path and os.path.exists(path):
                print(f"   📂 Найден путь: {path}")
                return path
        
        return None

    def _scan_directory(self, directory_path: str, max_files: int = 100):
        """
        Сканирует директорию на наличие изображений.
        
        Args:
            directory_path: Путь к директории
            max_files: Максимальное количество файлов для сканирования
        """
        if not os.path.exists(directory_path):
            return
        
        try:
            files = os.listdir(directory_path)
            count = 0
            
            for file in files:
                if count >= max_files:
                    break
                
                file_path = os.path.join(directory_path, file)
                if os.path.isfile(file_path):
                    ext = os.path.splitext(file)[1].lower()
                    if ext in self.IMAGE_EXTENSIONS:
                        metadata = self._get_photo_metadata(file_path)
                        self.photos.append(metadata)
                        count += 1
        except PermissionError:
            print(f"⚠️ Нет доступа к: {directory_path}")
        except Exception as e:
            print(f"⚠️ Ошибка сканирования {directory_path}: {e}")

    def _get_photo_metadata(self, file_path: str) -> Dict:
        """
        Собирает основные метаданные изображения.
        
        Args:
            file_path: Путь к файлу
        
        Returns:
            Dict: Словарь с метаданными
        """
        try:
            stat = os.stat(file_path)
            size_mb = round(stat.st_size / (1024 * 1024), 2)
            
            return {
                'path': file_path,
                'name': os.path.basename(file_path),
                'directory': os.path.dirname(file_path),
                'size_mb': size_mb,
                'modified': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M'),
                'created': datetime.fromtimestamp(stat.st_ctime).strftime('%Y-%m-%d %H:%M'),
            }
        except Exception as e:
            return {
                'path': file_path,
                'name': os.path.basename(file_path),
                'directory': os.path.dirname(file_path),
                'size_mb': 0,
                'modified': '',
                'created': '',
            }

    def get_recent_photos(self, limit: int = 50) -> List[Dict]:
        """
        Возвращает последние N фотографий (отсортированные по дате изменения).
        
        Args:
            limit: Количество фотографий
        
        Returns:
            List[Dict]: Список последних фотографий
        """
        if not self.photos:
            self.find_photos()
        
        sorted_photos = sorted(
            self.photos,
            key=lambda x: x.get('modified', ''),
            reverse=True
        )
        
        return sorted_photos[:limit]