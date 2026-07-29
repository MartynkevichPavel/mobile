import flet as ft
import os
import sys
import warnings
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

warnings.filterwarnings("ignore", category=RuntimeWarning)

from config import MODEL_PATH
from yolo_analyzer import YOLOAnalyzer
from database import PhotoDatabase
from utils import format_tags


analysis_results = {}
current_images = []


def analyze_single_image(image_path: str, analyzer_instance):
    try:
        detections = analyzer_instance.analyze(image_path)
        tags = [d['class'] for d in detections if d['confidence'] > 0.3]
        
        db = PhotoDatabase()
        db.add_photo(hash(image_path), image_path, tags)
        
        return {
            'path': image_path,
            'tags': tags,
            'detections': detections,
            'filename': os.path.basename(image_path),
            'success': True,
            'error': None
        }
    except Exception as e:
        return {
            'path': image_path,
            'tags': [],
            'detections': [],
            'filename': os.path.basename(image_path),
            'success': False,
            'error': str(e)
        }


def main(page: ft.Page):
    global current_images, analysis_results
    
    page.title = "Photo Analyzer"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 20
    page.scroll = ft.ScrollMode.AUTO

    executor = ThreadPoolExecutor(max_workers=4)
    
    model_path = MODEL_PATH
    analyzer = None

    title = ft.Text("📸 Photo Analyzer", size=32, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER)
    model_status = ft.Text("⏳ Загрузка модели...", size=14, color=ft.Colors.GREY)
    gallery_grid = ft.GridView(expand=True, max_extent=150, spacing=10, run_spacing=10)
    selected_info = ft.Text("Выбрано: 0 файлов", size=14, color=ft.Colors.GREY)
    progress_container = ft.Column()

    def show_snackbar(message: str, action: str = "OK"):
        """Показывает уведомление"""
        page.snack_bar = ft.SnackBar(
            content=ft.Text(message),
            action=action,
        )
        page.snack_bar.open = True
        page.update()

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
            show_snackbar(f"Выбрано файлов: {len(data)}")
        else:
            show_snackbar("Выбор отменен")

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
        
        # Пробуем разные варианты JavaScript
        if hasattr(page.window, 'evaluate_js'):
            page.window.evaluate_js(js_code)
        elif hasattr(page.window, 'run_javascript'):
            page.window.run_javascript(js_code)
        else:
            show_snackbar("Выбор файлов не доступен в этом режиме")
        
        page.on_js_message = on_files_selected

    def analyze_images():
        if not analyzer:
            show_snackbar("❌ Модель не загружена!")
            return

        if not current_images:
            show_snackbar("⚠️ Нет выбранных файлов!")
            return

        analysis_results.clear()
        gallery_grid.controls.clear()
        progress_container.controls.clear()

        progress_items = {}
        for path in current_images:
            filename = os.path.basename(path)
            progress_row = ft.Row([
                ft.Text(f"📷 {filename[:20]}...", size=12, width=150),
                ft.ProgressBar(width=200, value=0),
                ft.Text("⏳", size=14),
            ], alignment=ft.MainAxisAlignment.START)
            progress_container.controls.append(progress_row)
            progress_items[path] = {
                'row': progress_row,
                'bar': progress_row.controls[1],
                'status': progress_row.controls[2],
            }

        page.add(ft.Divider(height=10), progress_container)
        page.update()

        futures = []
        for path in current_images:
            future = executor.submit(analyze_single_image, path, analyzer)
            futures.append(future)

        def check_futures():
            completed = 0
            total = len(futures)
            for future in as_completed(futures):
                completed += 1
                result = future.result()
                path = result['path']
                
                if path in progress_items:
                    items = progress_items[path]
                    items['bar'].value = 1.0
                    items['status'].value = "✅" if result['success'] else "❌"
                    page.update()
                
                analysis_results[path] = {
                    'tags': result['tags'],
                    'detections': result['detections'],
                    'filename': result['filename'],
                    'success': result['success'],
                    'error': result['error']
                }
            
            show_snackbar(f"✅ Анализ завершен! Обработано: {completed} из {total}")
            show_results()

        threading.Thread(target=check_futures, daemon=True).start()

    def show_results():
        gallery_grid.controls.clear()
        for path, data in analysis_results.items():
            tags_str = format_tags(data['tags'])
            filename = data['filename'][:20] + "..." if len(data['filename']) > 20 else data['filename']
            status_icon = "✅" if data['success'] else "❌"

            card = ft.Container(
                content=ft.Column([
                    ft.Icon(ft.Icons.IMAGE, size=40, color=ft.Colors.BLUE_400),
                    ft.Text(filename, size=12, weight=ft.FontWeight.W_500, text_align=ft.TextAlign.CENTER),
                    ft.Text(f"🏷️ {tags_str}", size=11, color=ft.Colors.GREY_400, text_align=ft.TextAlign.CENTER),
                    ft.Text(f"🎯 {len(data['detections'])} объектов {status_icon}", size=11, color=ft.Colors.GREY_500, text_align=ft.TextAlign.CENTER),
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
    )

    load_btn = ft.Button(
        "🤖 Загрузить модель",
        icon=ft.Icons.MODEL_TRAINING,
        on_click=lambda e: load_model(),
    )

    analyze_btn = ft.Button(
        "🔍 Анализировать",
        icon=ft.Icons.SEARCH,
        on_click=lambda e: analyze_images(),
    )

    header = ft.Row([
        pick_btn,
        analyze_btn,
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


if __name__ == "__main__":
    ft.run(main, view=ft.AppView.WEB_BROWSER)