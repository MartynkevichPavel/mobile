import flet as ft
import os
import warnings
warnings.filterwarnings("ignore", category=RuntimeWarning)

from config import MODEL_PATH
from yolo_model import YOLOAnalyzer
from database import PhotoDatabase
from utils import format_tags


def main(page: ft.Page):
    # Настройка страницы
    page.title = "Photo Analyzer"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 20
    page.scroll = ft.ScrollMode.AUTO

    # Инициализация компонентов
    model_path = MODEL_PATH
    analyzer = None
    db = PhotoDatabase()

    # Состояние приложения
    current_images = []
    analysis_results = {}

    # ===================== UI КОМПОНЕНТЫ =====================

    title = ft.Text(
        "📸 Photo Analyzer",
        size=32,
        weight=ft.FontWeight.BOLD,
        text_align=ft.TextAlign.CENTER,
    )

    model_status = ft.Text(
        "⏳ Загрузка модели...",
        size=14,
        color=ft.Colors.GREY,
    )

    gallery_grid = ft.GridView(
        expand=True,
        max_extent=150,
        spacing=10,
        run_spacing=10,
    )

    selected_info = ft.Text(
        "Выбрано: 0 файлов",
        size=14,
        color=ft.Colors.GREY,
    )

    # ===================== ОБРАБОТЧИКИ СОБЫТИЙ =====================

    def load_model():
        nonlocal analyzer
        try:
            if os.path.exists(model_path):
                analyzer = YOLOAnalyzer(model_path)
                model_status.value = "✅ Модель загружена"
                model_status.color = ft.Colors.GREEN
            else:
                model_status.value = f"❌ Модель не найдена: {model_path}"
                model_status.color = ft.Colors.RED
        except Exception as e:
            model_status.value = f"❌ Ошибка: {str(e)}"
            model_status.color = ft.Colors.RED
        page.update()

    def on_files_selected(data):
        """Обработка файлов, выбранных через JavaScript"""
        print(f"📁 Получены файлы: {data}")
        if data and len(data) > 0:
            page.show_snack_bar(
                ft.SnackBar(
                    content=ft.Text(f"Выбрано файлов: {len(data)}"),
                    action="OK",
                )
            )
            page.update()

    def pick_files_web(e):
        """Открывает диалог выбора файлов через JavaScript"""
        js_code = """
        var input = document.createElement('input');
        input.type = 'file';
        input.multiple = true;
        input.accept = 'image/*';
        input.onchange = function(e) {
            var files = e.target.files;
            var result = [];
            for (var i = 0; i < files.length; i++) {
                result.push(files[i].name);
            }
            window._flet_file_picker_result = result;
            var event = new CustomEvent('file-picked', { detail: result });
            document.dispatchEvent(event);
        };
        input.click();
        """
        page.run_javascript(js_code)
        page.on_js_message = on_files_selected

    def analyze_images():
        if not analyzer:
            page.add(ft.Text("❌ Модель не загружена!", color=ft.Colors.RED))
            return

        if not current_images:
            return

        progress = ft.ProgressBar(width=400)
        progress_text = ft.Text("Анализ... 0%")
        progress_row = ft.Row([progress, progress_text], alignment=ft.MainAxisAlignment.CENTER)
        page.add(progress_row)
        page.update()

        for idx, path in enumerate(current_images):
            try:
                detections = analyzer.analyze(path)
                tags = [d['class'] for d in detections if d['confidence'] > 0.3]

                analysis_results[path] = {
                    'tags': tags,
                    'detections': detections,
                    'filename': os.path.basename(path)
                }

                db.add_photo(hash(path), path, tags)

                progress.value = (idx + 1) / len(current_images)
                progress_text.value = f"Анализ... {int(progress.value * 100)}%"
                page.update()

            except Exception as e:
                print(f"❌ Ошибка анализа {path}: {e}")

        page.remove(progress_row)
        page.update()
        show_results()

    def show_results():
        gallery_grid.controls.clear()

        for path, data in analysis_results.items():
            tags_str = format_tags(data['tags'])
            filename = data['filename'][:20] + "..." if len(data['filename']) > 20 else data['filename']

            card = ft.Container(
                content=ft.Column([
                    ft.Icon(ft.Icons.IMAGE, size=40, color=ft.Colors.BLUE_400),
                    ft.Text(
                        filename,
                        size=12,
                        weight=ft.FontWeight.W_500,
                        text_align=ft.TextAlign.CENTER,
                    ),
                    ft.Text(
                        f"🏷️ {tags_str}",
                        size=11,
                        color=ft.Colors.GREY_400,
                        text_align=ft.TextAlign.CENTER,
                    ),
                    ft.Text(
                        f"🎯 {len(data['detections'])} объектов",
                        size=11,
                        color=ft.Colors.GREY_500,
                        text_align=ft.TextAlign.CENTER,
                    ),
                ]),
                padding=10,
                bgcolor=ft.Colors.GREY_900,
                border_radius=10,
                width=150,
            )
            gallery_grid.controls.append(card)

        page.update()

    # ===================== КНОПКИ =====================

    pick_btn = ft.Button(
        "📁 Выбрать фото",
        icon=ft.Icons.PHOTO_LIBRARY,
        on_click=pick_files_web,
        style=ft.ButtonStyle(
            padding=ft.Padding.symmetric(horizontal=20, vertical=15),
            shape=ft.RoundedRectangleBorder(radius=10),
        ),
    )

    load_btn = ft.Button(
        "🤖 Загрузить модель",
        icon=ft.Icons.MODEL_TRAINING,
        on_click=lambda e: load_model(),
        style=ft.ButtonStyle(
            padding=ft.Padding.symmetric(horizontal=20, vertical=15),
            shape=ft.RoundedRectangleBorder(radius=10),
        ),
    )

    # ===================== СБОРКА ИНТЕРФЕЙСА =====================

    header = ft.Row([
        pick_btn,
        load_btn,
        selected_info,
    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)

    page.add(
        title,
        ft.Divider(height=20),
        model_status,
        ft.Divider(height=10),
        header,
        ft.Divider(height=10),
        gallery_grid,
    )

    load_model()
    page.update()


# ==========================================
# ЗАПУСК ПРИЛОЖЕНИЯ (ВЕБ-РЕЖИМ)
# ==========================================

if __name__ == "__main__":
    ft.run(main, view=ft.AppView.WEB_BROWSER)