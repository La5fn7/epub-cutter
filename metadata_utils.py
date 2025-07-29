#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Утилиты для извлечения метаданных из EPUB файлов
"""

def extract_epub_metadata(opf_root):
    """
    Извлекает название книги и автора из OPF файла
    
    Args:
        opf_root: XML элемент корня OPF файла
        
    Returns:
        tuple: (title, author)
    """
    book_title = "Без названия"
    book_author = "Автор неизвестен"
    
    try:
        # Поиск названия книги - пробуем разные варианты
        title_elem = opf_root.find('.//{http://purl.org/dc/elements/1.1/}title')
        if title_elem is not None and title_elem.text:
            book_title = title_elem.text.strip()
        else:
            # Альтернативный поиск без namespace
            title_elem = opf_root.find('.//title')
            if title_elem is not None and title_elem.text:
                book_title = title_elem.text.strip()
        
        # Поиск автора - пробуем разные варианты
        creator_elem = opf_root.find('.//{http://purl.org/dc/elements/1.1/}creator')
        if creator_elem is not None and creator_elem.text:
            book_author = creator_elem.text.strip()
        else:
            # Альтернативные поиски
            author_variants = [
                './/creator',
                './/{http://purl.org/dc/elements/1.1/}author', 
                './/author',
                './/{http://purl.org/dc/elements/1.1/}contributor[@opf:role="aut"]'
            ]
            
            for variant in author_variants:
                try:
                    author_elem = opf_root.find(variant)
                    if author_elem is not None and author_elem.text:
                        book_author = author_elem.text.strip()
                        break
                except:
                    continue
        
        # Очистка от лишних символов и длинных строк
        if book_title and len(book_title) > 100:
            book_title = book_title[:97] + "..."
            
        if book_author and len(book_author) > 80:
            book_author = book_author[:77] + "..."
            
    except Exception as e:
        print(f"Ошибка извлечения метаданных: {e}")
        
    return book_title, book_author

def format_book_info(title, author, style="basic"):
    """
    Форматирует информацию о книге для отображения
    
    Args:
        title: название книги
        author: автор
        style: стиль форматирования ("basic", "modern", "compact")
        
    Returns:
        str: отформатированная строка
    """
    if not title and not author:
        return ""
        
    if style == "modern":
        return f'📚 "{title}" — {author}'
    elif style == "compact":
        return f'"{title}" — {author}'
    else:  # basic
        return f'📖 "{title}" — {author}'