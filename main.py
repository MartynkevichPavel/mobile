"""
Точка входа для Flet мобильного приложения
"""
from src.main import main
import flet as ft

if __name__ == "__main__":
    ft.app(target=main, view=ft.AppView.FLET_APP)