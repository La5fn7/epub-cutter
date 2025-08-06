#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Анализ структуры PDF файла для правильного извлечения оглавления
"""

import sys
import os
from pathlib import Path

# Добавляем путь к pypdf
try:
    from pypdf import PdfReader
    print("+ pypdf imported successfully")
except ImportError:
    print("- Error importing pypdf")
    sys.exit(1)

def analyze_pdf_structure(pdf_path):
    """Анализирует структуру PDF файла"""
    print(f"\nAnalyzing PDF file: {pdf_path}")
    print("=" * 60)
    
    try:
        reader = PdfReader(pdf_path)
        print(f"Total pages: {len(reader.pages)}")
        
        # Анализ метаданных
        print(f"\nMetadata:")
        if reader.metadata:
            for key, value in reader.metadata.items():
                print(f"  {key}: {value}")
        else:
            print("  No metadata found")
        
        # Анализ outline (оглавление)
        print(f"\nOutline structure:")
        if reader.outline:
            print(f"  Found outline structure with {len(reader.outline)} elements")
            analyze_outline(reader.outline, reader, level=0)
        else:
            print("  No outline structure found")
        
        # Анализ первых страниц на предмет оглавления
        print(f"\nAnalyzing first 10 pages:")
        for i in range(min(10, len(reader.pages))):
            page = reader.pages[i]
            text = page.extract_text()
            
            # Ищем признаки оглавления
            lines = text.split('\n') if text else []
            chapter_patterns = []
            
            for line in lines[:20]:  # Первые 20 строк страницы
                line = line.strip()
                if not line:
                    continue
                    
                # Паттерны для поиска глав
                import re
                patterns = [
                    r'Chapter\s+\d+',
                    r'Глава\s+\d+',
                    r'CHAPTER\s+\d+',
                    r'\d+\.\s*[A-Z]',
                    r'Contents',
                    r'Table of Contents',
                    r'Introduction',
                    r'Preface'
                ]
                
                for pattern in patterns:
                    if re.search(pattern, line, re.IGNORECASE):
                        chapter_patterns.append(line)
                        break
            
            if chapter_patterns:
                print(f"  Page {i+1}: Found possible headings:")
                for pattern in chapter_patterns[:3]:  # Показываем первые 3
                    print(f"    '{pattern}'")
            
            # Проверяем ссылки на странице
            if '/Annots' in page:
                annotations = page['/Annots']
                link_count = 0
                for annot_ref in annotations:
                    try:
                        annot = annot_ref.get_object()
                        if annot.get('/Subtype') == '/Link':
                            link_count += 1
                    except Exception as e:
                        print(f"Ошибка при обработке аннотации: {e}")
                
                if link_count > 0:
                    print(f"  Page {i+1}: Found {link_count} interactive links")
    
    except Exception as e:
        print(f"Error analyzing PDF: {e}")
        import traceback
        traceback.print_exc()

def analyze_outline(outline, reader, level=0):
    """Рекурсивно анализирует outline структуру"""
    indent = "  " * (level + 1)
    
    for i, item in enumerate(outline):
        print(f"{indent}[{i}] Тип: {type(item)}")
        
        # Извлекаем заголовок
        title = "???"
        if hasattr(item, 'title'):
            title = item.title
        
        # Извлекаем номер страницы
        page_num = "???"
        if hasattr(item, 'page') and item.page is not None:
            try:
                if hasattr(reader, 'get_destination_page_number'):
                    page_num = reader.get_destination_page_number(item.page)
                else:
                    page_num = reader.getDestinationPageNumber(item.page)
            except Exception as e:
                page_num = f"Ошибка: {e}"
        
        print(f"{indent}> '{title}' -> page {page_num}")
        
        # Дополнительная информация об элементе
        if hasattr(item, '__dict__'):
            attrs = [attr for attr in dir(item) if not attr.startswith('_')]
            print(f"{indent}   Attributes: {attrs}")
        
        # Рекурсивно обрабатываем подэлементы
        if hasattr(item, '__iter__') and not isinstance(item, str):
            try:
                print(f"{indent}   Subelements:")
                analyze_outline(item, reader, level + 1)
            except Exception as e:
                print(f"Ошибка при анализе подэлементов outline: {e}")

if __name__ == "__main__":
    pdf_path = "books/Hearing Singing - Ian Howell.pdf"
    if os.path.exists(pdf_path):
        analyze_pdf_structure(pdf_path)
    else:
        print(f"PDF file not found: {pdf_path}")
        print("Available files in books/:")
        for file in Path("books").glob("*.pdf"):
            print(f"  {file.name}")