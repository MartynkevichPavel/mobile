import flet as ft
import os
import sys
import warnings
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError
import threading
import time

warnings.filterwarnings("ignore", category=RuntimeWarning)

from config import MODEL_PATH
from yolo_analyzer import YOLOAnalyzer
from database import PhotoDatabase
from utils import format_tags
from gallery_scanner import GalleryScanner


analysis_results = {}
current_images = []
is_analyzing = False
analysis_complete = False


def analyze_single_image(image_path: str, analyzer_instance):
    """Анализирует одно изображение (без сигналов)"""
    try:
        print(f"📸 Обработка: {os.path.basename(image_path)}")
        
        if not os.path.exists(image_path):
            return {
                'path': image_path,
                'tags': [],
                'detections': [],
                'filename': os.path.basename(image_path),
                'success': False,
                'error': 'File not found'
            }
        
        # Просто выполняем анализ (без сигналов)
        detections = analyzer_instance.analyze(image_path)
        tags = [d['class'] for d in detections if d['confidence'] > 0.3]
        
        try:
            db = PhotoDatabase()
            db.add_photo(hash(image_path), image_path, tags)
        except Exception as e:
            print(f"   ⚠️ БД: {e}")
        
        return {
            'path': image_path,
            'tags': tags,
            'detections': detections,
            'filename': os.path.basename(image_path),
            'success': True,
            'error': None
        }
    except Exception as e:
        print(f"❌ Ошибка {os.path.basename(image_path)}: {e}")
        return {
            'path': image_path,
            'tags': [],
            'detections': [],
            'filename': os.path.basename(image_path),
            'success': False,
            'error': str(e)
        }


def main(page: ft.Page):
    global current_images, analysis_results, is_analyzing, analysis_complete
    
    page.title = "Photo Analyzer"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 20
    page.scroll = ft.ScrollMode.AUTO

    executor = ThreadPoolExecutor(max_workers=2)
    
    model_path = MODEL_PATH
    analyzer = None
    scanner = GalleryScanner()
    
    # ===================== UI КОМПОНЕНТЫ =====================

    title = ft.Text("📸 Photo Analyzer", size=32, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER)
    
    model_status = ft.Text("⏳ Загрузка модели...", size=14, color=ft.Colors.GREY)
    
    status_text = ft.Text("Готов к работе", size=14, color=ft.Colors.GREY_500)
    
    selected_info = ft.Text("Выбрано: 0 файлов", size=14, color=ft.Colors.GREY)
    
    progress_container = ft.Column()
    
    gallery_grid = ft.GridView(
        expand=True,
        max_extent=150,
        spacing=10,
        run_spacing=10,
    )

    # ===================== ФУНКЦИИ =====================

    def show_snackbar(message: str, action: str = "OK"):
        page.snack_bar = ft.SnackBar(content=ft.Text(message), action=action)
        page.snack_bar.open = True
        page.update()

    def load_model():
        nonlocal analyzer
        try:
            if os.path.exists(model_path):
                analyzer = YOLOAnalyzer(model_path)
                model_status.value = "✅ Модель загружена"
                model_status.color = ft.Colors.GREEN
                status_text.value = "Готов к анализу"
            else:
                model_status.value = f"❌ Модель не найдена: {model_path}"
                model_status.color = ft.Colors.RED
        except Exception as e:
            model_status.value = f"❌ Ошибка: {str(e)}"
            model_status.color = ft.Colors.RED
        page.update()

    def find_gallery_async():
        def search_thread():
            try:
                status_text.value = "⏳ Поиск фото..."
                page.update()
                
                photos = scanner.find_photos()
                
                if not photos:
                    status_text.value = "❌ Фото не найдены"
                    page.update()
                    show_snackbar("❌ Фото не найдены")
                    return
                
                current_images.clear()
                for photo in photos:
                    if photo.get('path'):
                        current_images.append(photo['path'])
                
                selected_info.value = f"Найдено: {len(current_images)} фото"
                status_text.value = f"Готово: {len(current_images)} фото"
                page.update()
                
                show_snackbar(f"Найдено {len(current_images)} фото")
                
            except Exception as e:
                status_text.value = f"❌ Ошибка: {e}"
                page.update()
                show_snackbar(f"Ошибка: {e}")
        
        threading.Thread(target=search_thread, daemon=True).start()

    def find_gallery(e):
        find_gallery_async()

    def pick_files_desktop(e):
        try:
            import tkinter as tk
            from tkinter import filedialog
            
            root = tk.Tk()
            root.withdraw()
            root.attributes('-topmost', True)
            
            files = filedialog.askopenfilenames(
                title="Выберите фотографии",
                filetypes=[("Image files", "*.jpg *.jpeg *.png *.bmp *.webp")]
            )
            root.destroy()
            
            if files:
                current_images.clear()
                for f in files:
                    current_images.append(f)
                selected_info.value = f"Выбрано: {len(current_images)} файлов"
                status_text.value = f"Готово: {len(current_images)} файлов"
                page.update()
                show_snackbar(f"Выбрано {len(current_images)} файлов")
            else:
                show_snackbar("Выбор отменен")
        except Exception as e:
            show_snackbar(f"Ошибка: {e}")

    def pick_files(e):
        pick_files_desktop(e)

    def analyze_images():
        global is_analyzing, analysis_complete
        
        if is_analyzing:
            show_snackbar("⏳ Анализ уже выполняется!")
            return
        
        if not analyzer:
            show_snackbar("❌ Модель не загружена!")
            return

        if not current_images:
            show_snackbar("⚠️ Нет выбранных файлов!")
            return

        # Сбрасываем предыдущие результаты
        is_analyzing = True
        analysis_complete = False
        analysis_results.clear()
        gallery_grid.controls.clear()
        progress_container.controls.clear()
        
        # Обновляем кнопки
        analyze_btn.text = "⏳ Анализ..."
        analyze_btn.disabled = True
        show_results_btn.disabled = True
        page.update()

        # Создаем прогресс-бары
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
        status_text.value = f"⏳ Анализ: 0/{len(current_images)}"
        page.update()

        # Запускаем задачи
        futures = []
        for path in current_images:
            future = executor.submit(analyze_single_image, path, analyzer)
            futures.append(future)

        def check_futures():
            global is_analyzing, analysis_complete
            completed = 0
            total = len(futures)
            
            for future in as_completed(futures):
                completed += 1
                try:
                    result = future.result(timeout=60)
                    path = result['path']
                    
                    if path in progress_items:
                        items = progress_items[path]
                        items['bar'].value = 1.0
                        if result['success'] and result['detections']:
                            items['status'].value = f"✅ {len(result['detections'])}"
                        elif result['success']:
                            items['status'].value = "⚠️ 0"
                        else:
                            items['status'].value = "❌"
                        page.update()
                    
                    analysis_results[path] = {
                        'tags': result['tags'],
                        'detections': result['detections'],
                        'filename': result['filename'],
                        'success': result['success'],
                        'error': result['error']
                    }
                    
                except TimeoutError:
                    print(f"⏰ Таймаут задачи {completed}/{total}")
                    # Добавляем пустой результат
                    path = f"unknown_{completed}"
                    analysis_results[path] = {
                        'tags': [],
                        'detections': [],
                        'filename': f"Задача {completed}",
                        'success': False,
                        'error': 'Timeout'
                    }
                    
                except Exception as e:
                    print(f"❌ Ошибка: {e}")
                
                status_text.value = f"⏳ Анализ: {completed}/{total}"
                page.update()
            
            # Анализ завершен
            is_analyzing = False
            analysis_complete = True
            
            total_detections = sum(len(r['detections']) for r in analysis_results.values())
            status_text.value = f"✅ Анализ завершен! Найдено объектов: {total_detections}"
            
            analyze_btn.text = "🔍 Анализировать"
            analyze_btn.disabled = False
            show_results_btn.disabled = False
            
            show_snackbar(f"✅ Анализ завершен! Найдено объектов: {total_detections}")
            
            # Автоматически показываем результаты
            show_results()

        threading.Thread(target=check_futures, daemon=True).start()

    def show_results():
        if not analysis_results:
            show_snackbar("⚠️ Нет результатов для отображения")
            return
        
        gallery_grid.controls.clear()
        
        for path, data in analysis_results.items():
            tags_str = format_tags(data['tags'])
            filename = data['filename'][:20] + "..." if len(data['filename']) > 20 else data['filename']
            
            if data['success'] and data['detections']:
                status_icon = f"✅ {len(data['detections'])}"
            elif data['success']:
                status_icon = "⚠️ 0"
            else:
                status_icon = "❌"

            card = ft.Container(
                content=ft.Column([
                    ft.Icon(ft.Icons.IMAGE, size=40, color=ft.Colors.BLUE_400),
                    ft.Text(filename, size=12, weight=ft.FontWeight.W_500, text_align=ft.TextAlign.CENTER),
                    ft.Text(f"🏷️ {tags_str}", size=11, color=ft.Colors.GREY_400, text_align=ft.TextAlign.CENTER),
                    ft.Text(f"🎯 {status_icon}", size=11, color=ft.Colors.GREY_500, text_align=ft.TextAlign.CENTER),
                ]),
                padding=10,
                bgcolor=ft.Colors.GREY_900,
                border_radius=10,
                width=150,
            )
            gallery_grid.controls.append(card)
        
        page.update()
        show_snackbar(f"✅ Отображено {len(analysis_results)} результатов")

    # ===================== КНОПКИ =====================

    search_btn = ft.Button(
        "📂 Найти фото",
        icon=ft.Icons.SEARCH,
        on_click=find_gallery,
    )

    pick_btn = ft.Button(
        "📁 Выбрать фото",
        icon=ft.Icons.PHOTO_LIBRARY,
        on_click=pick_files,
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

    show_results_btn = ft.Button(
        "📊 Показать результаты",
        icon=ft.Icons.LIST,
        on_click=lambda e: show_results(),
        disabled=True,
    )

    # ===================== СБОРКА ИНТЕРФЕЙСА =====================

    header = ft.Row([
        search_btn,
        pick_btn,
        analyze_btn,
        show_results_btn,
        load_btn,
    ], alignment=ft.MainAxisAlignment.START, wrap=True, spacing=10)

    page.add(
        title,
        ft.Divider(height=20),
        model_status,
        ft.Divider(height=10),
        header,
        ft.Divider(height=10),
        selected_info,
        status_text,
        ft.Divider(height=10),
        gallery_grid,
    )

    load_model()
    page.update()


if __name__ == "__main__":
    ft.run(main, view=ft.AppView.FLET_APP)