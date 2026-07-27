import flet as ft

def main(page: ft.Page):
    page.title = "Test"
    page.theme_mode = ft.ThemeMode.LIGHT
    
    page.add(
        ft.Text("Hello World!", size=30),
        ft.Text("Десктоп-режим", size=16, color=ft.Colors.GREY),
    )
    page.update()

if __name__ == "__main__":
    ft.run(main, view=ft.AppView.FLET_APP)