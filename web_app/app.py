#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Web-приложение EPUB Cutter
Современное веб-интерфейс для создания сайтов из EPUB книг
"""

import os
import json
import sqlite3
import zipfile
from pathlib import Path
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_from_directory, redirect, url_for
from werkzeug.utils import secure_filename
import sys

# Добавляем родительскую директорию в путь для импорта модулей
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from metadata_utils import extract_epub_metadata, format_book_info

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-change-in-production'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['BOOKS_FOLDER'] = 'books'
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB max file size

# Убеждаемся, что папки существуют
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['BOOKS_FOLDER'], exist_ok=True)

class EPUBProcessor:
    """Класс для обработки EPUB файлов (адаптирован из основного приложения)"""
    
    def __init__(self):
        self.book_title = ""
        self.book_author = ""
        self.chapters = []
        self.images = {}
    
    def load_epub(self, epub_path):
        """Загружает EPUB файл и извлекает главы"""
        try:
            self.chapters.clear()
            self.images.clear()
            
            with zipfile.ZipFile(epub_path, 'r') as epub_zip:
                # Чтение структуры EPUB
                from xml.etree import ElementTree as ET
                
                container_xml = epub_zip.read('META-INF/container.xml')
                container_root = ET.fromstring(container_xml)
                
                opf_path = container_root.find('.//{urn:oasis:names:tc:opendocument:xmlns:container}rootfile').get('full-path')
                opf_content = epub_zip.read(opf_path)
                opf_root = ET.fromstring(opf_content)
                
                # Извлечение метаданных книги
                self.book_title, self.book_author = extract_epub_metadata(opf_root)
                
                # Загрузка изображений
                opf_dir = os.path.dirname(opf_path)
                for item in opf_root.findall('.//{http://www.idpf.org/2007/opf}item'):
                    media_type = item.get('media-type', '')
                    if media_type.startswith('image/'):
                        href = item.get('href')
                        if href:
                            img_path = os.path.join(opf_dir, href).replace('\\', '/')
                            try:
                                img_data = epub_zip.read(img_path)
                                self.images[img_path] = img_data
                            except:
                                pass
                
                # Загрузка глав
                spine_items = opf_root.findall('.//{http://www.idpf.org/2007/opf}itemref')
                manifest_items = {item.get('id'): item for item in opf_root.findall('.//{http://www.idpf.org/2007/opf}item')}
                
                # Создаем маппинг файлов для будущих ссылок
                self.file_mapping = {}
                
                for i, spine_item in enumerate(spine_items):
                    idref = spine_item.get('idref')
                    if idref in manifest_items:
                        manifest_item = manifest_items[idref]
                        href = manifest_item.get('href')
                        media_type = manifest_item.get('media-type')
                        
                        if media_type == 'application/xhtml+xml':
                            file_path = os.path.join(opf_dir, href).replace('\\', '/')
                            
                            try:
                                chapter_content = epub_zip.read(file_path)
                                chapter_root = ET.fromstring(chapter_content)
                                
                                # Получение заголовка
                                title_elem = chapter_root.find('.//{http://www.w3.org/1999/xhtml}title')
                                title = title_elem.text if title_elem is not None and title_elem.text else f"Глава {i+1}"
                                
                                if title == f"Глава {i+1}":
                                    for tag in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                                        heading = chapter_root.find(f'.//{{{http://www.w3.org/1999/xhtml}}}{tag}')
                                        if heading is not None and heading.text:
                                            title = heading.text.strip()
                                            break
                                
                                import re
                                title = re.sub(r'[<>:"/\\|?*]', '', title)
                                
                                self.chapters.append({
                                    'title': title,
                                    'file_path': file_path,
                                    'content': chapter_content
                                })
                                
                                # Сохраняем маппинг для обработки ссылок
                                self.file_mapping[file_path] = len(self.chapters) - 1
                                
                            except Exception as e:
                                print(f"Ошибка при чтении главы {file_path}: {e}")
                                continue
            
            return True
            
        except Exception as e:
            print(f"Ошибка при загрузке EPUB: {e}")
            return False
    
    def create_website(self, output_path):
        """Создает веб-сайт из загруженной книги"""
        try:
            import re
            import html
            
            # Создание главной папки сайта
            site_name = re.sub(r'[<>:"/\\|?*]', '', self.book_title)
            site_path = Path(output_path) / site_name
            site_path.mkdir(parents=True, exist_ok=True)
            
            # Создание папки для изображений
            images_path = site_path / "images"
            images_path.mkdir(exist_ok=True)
            
            # CSS стили (из основного приложения)
            css_content = self._get_website_css()
            with open(site_path / "styles.css", 'w', encoding='utf-8') as f:
                f.write(css_content)
            
            # Создание index.html
            self._create_index_html(site_path)
            
            # Создание страниц глав с навигацией
            selected_chapters = [(i, chapter) for i, chapter in enumerate(self.chapters)]
            
            for idx, (i, chapter) in enumerate(selected_chapters):
                chapter_num = i + 1
                safe_title = re.sub(r'[<>:"/\\|?*]', '', chapter['title'])
                filename = f"chapter_{chapter_num:02d}_{safe_title}.html"
                filepath = site_path / filename
                
                # Обработка содержимого главы
                content = chapter['content'].decode('utf-8')
                content = content.replace('xmlns="http://www.w3.org/1999/xhtml"', '')
                
                # Обработка изображений
                content = self._process_images_for_website(content, images_path)
                
                # Обработка внутренних ссылок
                content = self._process_internal_links(content, selected_chapters, idx)
                
                # Создание навигации
                prev_link = ""
                next_link = ""
                
                if idx > 0:
                    prev_chapter = selected_chapters[idx-1][1]
                    prev_safe_title = re.sub(r'[<>:"/\\|?*]', '', prev_chapter['title'])
                    prev_num = selected_chapters[idx-1][0] + 1
                    prev_filename = f"chapter_{prev_num:02d}_{prev_safe_title}.html"
                    prev_link = f'<a href="{prev_filename}" class="nav-button">← Предыдущая</a>'
                
                if idx < len(selected_chapters) - 1:
                    next_chapter = selected_chapters[idx+1][1]
                    next_safe_title = re.sub(r'[<>:"/\\|?*]', '', next_chapter['title'])
                    next_num = selected_chapters[idx+1][0] + 1
                    next_filename = f"chapter_{next_num:02d}_{next_safe_title}.html"
                    next_link = f'<a href="{next_filename}" class="nav-button">Следующая →</a>'
                
                # Создание полного HTML документа главы
                chapter_html = f"""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{html.escape(chapter['title'])} - {html.escape(self.book_title)}</title>
    <link rel="stylesheet" href="styles.css">
</head>
<body>
    <div class="book-header">
        <h1 class="book-title">{html.escape(self.book_title)}</h1>
        <p class="book-author">{html.escape(self.book_author)}</p>
    </div>
    
    <div class="navigation">
        <a href="index.html" class="nav-button">📚 Содержание</a>
        {prev_link}
        {next_link}
    </div>
    
    <div class="chapter-content">
        {content}
    </div>
    
    <div class="navigation">
        <a href="index.html" class="nav-button">📚 Содержание</a>
        {prev_link}
        {next_link}
    </div>
</body>
</html>"""
                
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(chapter_html)
            
            return str(site_path)
            
        except Exception as e:
            print(f"Ошибка при создании сайта: {e}")
            return None
    
    def _create_index_html(self, site_path):
        """Создает главную страницу с оглавлением"""
        import html
        import re
        
        selected_chapters = [(i, chapter) for i, chapter in enumerate(self.chapters)]
        
        # Создаем словарь соответствий для ссылок в оглавлении
        self._create_chapter_mapping(selected_chapters)
        
        html_content = f"""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{self.book_title}</title>
    <link rel="stylesheet" href="styles.css">
</head>
<body>
    <div class="book-header">
        <h1 class="book-title">{html.escape(self.book_title)}</h1>
        <p class="book-author">{html.escape(self.book_author)}</p>
    </div>
    
    <div class="toc">
        <h2>📚 Содержание</h2>
        <ul>
"""
        
        for i, (chapter_idx, chapter) in enumerate(selected_chapters):
            chapter_num = chapter_idx + 1
            safe_title = re.sub(r'[<>:"/\\|?*]', '', chapter['title'])
            filename = f"chapter_{chapter_num:02d}_{safe_title}.html"
            
            html_content += f"""            <li>
                <a href="{filename}">
                    <span>{html.escape(chapter['title'])}</span>
                    <span class="chapter-number">{chapter_num}</span>
                </a>
            </li>
"""
        
        html_content += f"""        </ul>
    </div>
    
    <div class="navigation">
        <p>Эта книга содержит {len(selected_chapters)} глав. Выберите главу из оглавления выше для чтения.</p>
    </div>
</body>
</html>"""
        
        with open(site_path / "index.html", 'w', encoding='utf-8') as f:
            f.write(html_content)
    
    def _process_images_for_website(self, content, images_path):
        """Обрабатывает изображения для веб-сайта"""
        import re
        
        img_pattern = r'<img[^>]*src=["\']([^"\']+)["\'][^>]*>'
        
        def replace_img(match):
            img_tag = match.group(0)
            src = match.group(1)
            src_clean = src.replace('../', '').replace('./', '')
            
            # Ищем изображение по имени файла
            for img_path, img_data in self.images.items():
                img_filename = os.path.basename(img_path)
                src_filename = os.path.basename(src_clean)
                
                if img_filename == src_filename:
                    # Сохраняем изображение в папку images
                    img_filepath = images_path / img_filename
                    with open(img_filepath, 'wb') as f:
                        f.write(img_data)
                    
                    # Заменяем путь в HTML
                    relative_path = f"images/{img_filename}"
                    new_img_tag = img_tag.replace(f'src="{src}"', f'src="{relative_path}"')
                    new_img_tag = new_img_tag.replace(f"src='{src}'", f'src="{relative_path}"')
                    return new_img_tag
                    
            return img_tag
        
        return re.sub(img_pattern, replace_img, content)
    
    def _process_internal_links(self, content, selected_chapters, current_idx):
        """Обрабатывает внутренние ссылки между главами"""
        import re
        
        # Создаем словарь соответствий: исходный файл -> новый файл
        link_mapping = {}
        
        for idx, (i, chapter) in enumerate(selected_chapters):
            original_path = chapter['file_path']
            # Получаем имя исходного файла без пути
            original_filename = original_path.split('/')[-1]
            
            # Создаем имя нового файла
            chapter_num = i + 1
            safe_title = re.sub(r'[<>:"/\\|?*]', '', chapter['title'])
            new_filename = f"chapter_{chapter_num:02d}_{safe_title}.html"
            
            # Добавляем различные варианты ссылок
            link_mapping[original_filename] = new_filename
            link_mapping[original_path] = new_filename
            
            # Также обрабатываем относительные пути
            if '../' in original_path:
                relative_path = original_path.replace('../', '')
                link_mapping[relative_path] = new_filename
            
            # Обрабатываем пути без расширения (часто используется в ссылках)
            name_without_ext = original_filename.replace('.xhtml', '').replace('.html', '')
            link_mapping[name_without_ext] = new_filename
            
            # Также добавляем вариант с точкой в начале (относительный путь)
            if not original_filename.startswith('./'):
                link_mapping['./' + original_filename] = new_filename
        
        # Паттерн для поиска ссылок
        link_patterns = [
            r'<a[^>]*href=["\'](.*?)["\'][^>]*>',  # обычные ссылки
            r'href=["\'](.*?)["\']',  # просто href атрибуты
        ]
        
        def replace_link(match):
            full_match = match.group(0)
            href_value = match.group(1)
            
            # Пропускаем внешние ссылки и якоря
            if href_value.startswith(('http:', 'https:', 'mailto:', '#')):
                return full_match
            
            # Разделяем ссылку на файл и якорь
            if '#' in href_value:
                file_part, anchor_part = href_value.split('#', 1)
                anchor = '#' + anchor_part
            else:
                file_part = href_value
                anchor = ''
            
            # Убираем относительные пути
            clean_file = file_part.replace('../', '').replace('./', '')
            
            # Ищем соответствие в нашем словаре
            new_filename = None
            
            # Прямое совпадение
            if clean_file in link_mapping:
                new_filename = link_mapping[clean_file]
            else:
                # Поиск по частичному совпадению имени файла
                for original, new in link_mapping.items():
                    if clean_file in original or original.endswith(clean_file):
                        new_filename = new
                        break
            
            if new_filename:
                new_href = new_filename + anchor
                # Отладочный вывод (можно убрать в продакшене)
                if file_part != new_filename:
                    print(f"Заменяем ссылку: {href_value} -> {new_href}")
                return full_match.replace(href_value, new_href)
            
            return full_match
        
        # Применяем замены для всех паттернов
        for pattern in link_patterns:
            content = re.sub(pattern, replace_link, content)
        
        return content
    
    def _create_chapter_mapping(self, selected_chapters):
        """Создает маппинг исходных файлов на новые имена файлов"""
        import re
        self.chapter_mapping = {}
        
        for idx, (i, chapter) in enumerate(selected_chapters):
            original_path = chapter['file_path']
            original_filename = original_path.split('/')[-1]
            
            chapter_num = i + 1
            safe_title = re.sub(r'[<>:"/\\|?*]', '', chapter['title'])
            new_filename = f"chapter_{chapter_num:02d}_{safe_title}.html"
            
            # Различные варианты ссылок
            self.chapter_mapping[original_filename] = new_filename
            self.chapter_mapping[original_path] = new_filename
            
            if '../' in original_path:
                relative_path = original_path.replace('../', '')
                self.chapter_mapping[relative_path] = new_filename
            
            name_without_ext = original_filename.replace('.xhtml', '').replace('.html', '')
            self.chapter_mapping[name_without_ext] = new_filename
    
    def _get_website_css(self):
        """Возвращает CSS стили для сайта"""
        return """
        body {
            font-family: Georgia, "Times New Roman", serif;
            line-height: 1.6;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background-color: #fefefe;
            color: #333;
        }
        
        .book-header {
            text-align: center;
            border-bottom: 2px solid #007acc;
            padding-bottom: 20px;
            margin-bottom: 30px;
        }
        
        .book-title {
            font-size: 2.5em;
            color: #007acc;
            margin-bottom: 10px;
        }
        
        .book-author {
            font-size: 1.3em;
            color: #666;
            font-style: italic;
        }
        
        .toc {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            border-left: 4px solid #007acc;
        }
        
        .toc h2 {
            color: #007acc;
            margin-top: 0;
        }
        
        .toc ul {
            list-style: none;
            padding: 0;
        }
        
        .toc li {
            padding: 8px 0;
            border-bottom: 1px solid #eee;
        }
        
        .toc li:last-child {
            border-bottom: none;
        }
        
        .toc a {
            text-decoration: none;
            color: #333;
            font-weight: 500;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .toc a:hover {
            color: #007acc;
            background-color: #e3f2fd;
            padding: 5px 10px;
            border-radius: 4px;
            margin: -5px -10px;
        }
        
        .chapter-number {
            background: #007acc;
            color: white;
            padding: 2px 8px;
            border-radius: 12px;
            font-size: 0.8em;
            min-width: 20px;
            text-align: center;
        }
        
        .chapter-content {
            margin-top: 30px;
            padding: 20px;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        
        .navigation {
            margin: 30px 0;
            text-align: center;
        }
        
        .nav-button {
            background: #007acc;
            color: white;
            padding: 10px 20px;
            text-decoration: none;
            border-radius: 5px;
            margin: 0 10px;
            display: inline-block;
        }
        
        .nav-button:hover {
            background: #005c99;
        }
        
        img {
            max-width: 100%;
            height: auto;
            display: block;
            margin: 20px auto;
            border-radius: 4px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        
        @media (max-width: 600px) {
            body {
                padding: 10px;
            }
            
            .book-title {
                font-size: 2em;
            }
            
            .nav-button {
                display: block;
                margin: 10px 0;
            }
        }
        """

# Инициализация базы данных
def init_db():
    """Инициализирует базу данных для хранения информации о книгах"""
    conn = sqlite3.connect('books.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            original_filename TEXT NOT NULL,
            site_path TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            chapters_count INTEGER DEFAULT 0
        )
    ''')
    
    conn.commit()
    conn.close()

# Маршруты Flask
@app.route('/')
def index():
    """Главная страница с каталогом книг"""
    # Получаем список всех книг из базы данных
    conn = sqlite3.connect('books.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM books ORDER BY created_at DESC')
    books = cursor.fetchall()
    conn.close()
    
    return render_template('index.html', books=books)

@app.route('/upload', methods=['GET', 'POST'])
def upload_book():
    """Страница загрузки новой книги"""
    if request.method == 'POST':
        # Проверяем, что файл был загружен
        if 'file' not in request.files:
            return jsonify({'error': 'Файл не выбран'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'Файл не выбран'}), 400
        
        if file and file.filename.lower().endswith('.epub'):
            # Сохраняем загруженный файл
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            
            # Обрабатываем EPUB файл
            processor = EPUBProcessor()
            if processor.load_epub(file_path):
                # Создаем веб-сайт книги
                site_path = processor.create_website(app.config['BOOKS_FOLDER'])
                
                if site_path:
                    # Сохраняем информацию в базу данных
                    conn = sqlite3.connect('books.db')
                    cursor = conn.cursor()
                    # Получаем относительный путь от папки books
                    relative_site_path = os.path.relpath(site_path, app.config['BOOKS_FOLDER']).replace('\\', '/')
                    cursor.execute('''
                        INSERT INTO books (title, author, original_filename, site_path, chapters_count)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (processor.book_title, processor.book_author, filename, 
                          relative_site_path, len(processor.chapters)))
                    book_id = cursor.lastrowid
                    conn.commit()
                    conn.close()
                    
                    # Удаляем временный файл
                    os.remove(file_path)
                    
                    return jsonify({
                        'success': True,
                        'book_id': book_id,
                        'title': processor.book_title,
                        'author': processor.book_author,
                        'chapters_count': len(processor.chapters),
                        'site_path': relative_site_path
                    })
                else:
                    return jsonify({'error': 'Ошибка при создании сайта книги'}), 500
            else:
                return jsonify({'error': 'Ошибка при обработке EPUB файла'}), 500
        else:
            return jsonify({'error': 'Недопустимый формат файла. Поддерживается только EPUB'}), 400
    
    return render_template('upload.html')

@app.route('/book/<path:book_path>')
def view_book(book_path):
    """Просмотр конкретной книги"""
    return send_from_directory(app.config['BOOKS_FOLDER'], book_path)

@app.route('/book/<path:book_path>/<path:filename>')
def book_file(book_path, filename):
    """Обслуживание файлов книги (HTML, CSS, изображения)"""
    full_path = os.path.join(app.config['BOOKS_FOLDER'], book_path)
    return send_from_directory(full_path, filename)

@app.route('/delete/<int:book_id>', methods=['POST'])
def delete_book(book_id):
    """Удаление книги"""
    conn = sqlite3.connect('books.db')
    cursor = conn.cursor()
    cursor.execute('SELECT site_path FROM books WHERE id = ?', (book_id,))
    result = cursor.fetchone()
    
    if result:
        site_path = result[0]
        # Удаляем папку с сайтом книги
        import shutil
        full_site_path = os.path.join(app.config['BOOKS_FOLDER'], site_path)
        if os.path.exists(full_site_path):
            shutil.rmtree(full_site_path)
        
        # Удаляем запись из базы данных
        cursor.execute('DELETE FROM books WHERE id = ?', (book_id,))
        conn.commit()
        conn.close()
        
        return jsonify({'success': True})
    else:
        conn.close()
        return jsonify({'error': 'Книга не найдена'}), 404

if __name__ == '__main__':
    # Инициализируем базу данных
    init_db()
    
    # Запускаем приложение
    print("=== Запуск EPUB Cutter Web App ===")
    print("Откройте браузер и перейдите по адресу: http://localhost:5000")
    print("Загружайте EPUB файлы и создавайте веб-сайты книг!")
    
    app.run(debug=True, host='0.0.0.0', port=5000)