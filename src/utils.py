import os


def get_file_path(filename: str) -> str:
    """Возвращает абсолютный путь к файлу"""
    return os.path.abspath(filename)


def get_file_size(filepath: str) -> int:
    """Возвращает размер файла в байтах"""
    return os.path.getsize(filepath) if os.path.exists(filepath) else 0


def format_tags(tags: list) -> str:
    """Форматирует список тегов в строку"""
    return ", ".join(tags) if tags else "❌ Нет объектов"