#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Создание тестового PDF файла для отладки
"""

try:
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import letter
    
    def create_test_pdf():
        """Создает простой тестовый PDF файл"""
        filename = "test.pdf"
        c = canvas.Canvas(filename, pagesize=letter)
        
        # Страница 1
        c.drawString(100, 750, "Тестовый PDF документ")
        c.drawString(100, 730, "Страница 1")
        c.drawString(100, 710, "Это тестовый контент для проверки обработки PDF файлов.")
        c.drawString(100, 690, "Lorem ipsum dolor sit amet, consectetur adipiscing elit.")
        c.showPage()
        
        # Страница 2
        c.drawString(100, 750, "Страница 2")
        c.drawString(100, 730, "Продолжение тестового контента.")
        c.drawString(100, 710, "Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.")
        c.showPage()
        
        # Страница 3
        c.drawString(100, 750, "Страница 3")
        c.drawString(100, 730, "Финальная страница тестового документа.")
        c.drawString(100, 710, "Ut enim ad minim veniam, quis nostrud exercitation.")
        
        c.save()
        print(f"Тестовый PDF файл создан: {filename}")
        return filename
    
    if __name__ == "__main__":
        create_test_pdf()
        
except ImportError:
    print("Ошибка: модуль reportlab не найден. Установите: pip install reportlab")