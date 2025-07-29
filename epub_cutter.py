import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import tkinter.font as tkFont
from tkinter import scrolledtext
import zipfile
import os
import re
from pathlib import Path
from xml.etree import ElementTree as ET
import html
import threading
from tkinterdnd2 import TkinterDnD, DND_FILES

def get_safe_font(preferred_fonts, default_size=12, style="normal"):
    """
    Безопасная функция для выбора доступного шрифта
    """
    try:
        available_fonts = tkFont.families()
        
        for font_name in preferred_fonts:
            if font_name in available_fonts:
                if style == "bold":
                    return (font_name, default_size, "bold")
                elif style == "normal":
                    return (font_name, default_size)
                else:
                    return (font_name, default_size, style)
    except:
        pass
    
    # Если ни один из предпочитаемых шрифтов не найден, используем системный по умолчанию
    try:
        if style == "bold":
            return ("TkDefaultFont", default_size, "bold")
        elif style == "normal":
            return ("TkDefaultFont", default_size)
        else:
            return ("TkDefaultFont", default_size, style)
    except:
        # Крайний случай - используем базовый шрифт
        return ("Arial", default_size) if style == "normal" else ("Arial", default_size, style)

class ModernButton(tk.Frame):
    def __init__(self, parent, text, command=None, icon=None, style="primary", **kwargs):
        super().__init__(parent, **kwargs)
        
        self.command = command
        self.style = style
        
        # Нейтральная цветовая схема (серо-голубая)
        colors = {
            "primary": {"bg": "#007acc", "hover": "#1e80c7", "text": "#ffffff"},
            "secondary": {"bg": "#4a4a4a", "hover": "#5a5a5a", "text": "#ffffff"},
            "success": {"bg": "#6c7b7f", "hover": "#7a8a8f", "text": "#ffffff"},
            "danger": {"bg": "#d14343", "hover": "#e55353", "text": "#ffffff"}
        }
        
        self.color = colors.get(style, colors["primary"])
        
        self.btn = tk.Button(self, 
                            text=text,
                            command=command,
                            bg=self.color["bg"],
                            fg=self.color["text"],
                            font=get_safe_font(["Segoe UI", "Arial", "Helvetica"], 9, "bold"),
                            relief="flat",
                            bd=0,
                            padx=12,
                            pady=6,
                            cursor="hand2")
        self.btn.pack()
        
        self.btn.bind("<Enter>", lambda e: self.btn.configure(bg=self.color["hover"]))
        self.btn.bind("<Leave>", lambda e: self.btn.configure(bg=self.color["bg"]))

class EditableLabel(tk.Frame):
    def __init__(self, parent, text, callback=None, app_instance=None, **kwargs):
        super().__init__(parent, **kwargs)
        
        self.callback = callback
        self.original_text = text
        self.current_text = text
        self.editing = False
        self.app = app_instance  # Ссылка на главное приложение
        
        # Настройка цветов
        self.bg_color = self.master.master.colors["panel"] if hasattr(self.master.master, 'colors') else "#2d2d2d"
        self.text_color = "#ffffff"
        self.edit_bg = "#1a1a1a"
        
        self.configure(bg=self.bg_color)
        
        # Label для отображения - выровнен по левому краю, шрифт 12px
        self.label = tk.Label(self, 
                             text=text,
                             bg=self.bg_color,
                             fg=self.text_color,
                             font=get_safe_font(["Segoe UI", "Arial", "Helvetica"], 12, "normal"),
                             cursor="hand2",
                             anchor="w")
        self.label.pack(fill="both", expand=True, anchor="w")
        
        # Entry для редактирования (скрыт изначально)
        self.entry = tk.Entry(self,
                             bg=self.edit_bg,
                             fg=self.text_color,
                             font=get_safe_font(["Segoe UI", "Arial", "Helvetica"], 10, "normal"),
                             relief="flat",
                             bd=1)
        
        # События
        self.label.bind("<Double-Button-1>", self.start_edit)
        self.entry.bind("<Return>", self.finish_edit)
        self.entry.bind("<Escape>", self.cancel_edit)
        self.entry.bind("<FocusOut>", self.finish_edit)
        
    def start_edit(self, event=None):
        if self.editing:
            return
            
        # Завершить редактирование другого элемента, если он активен
        if self.app and self.app.currently_editing and self.app.currently_editing != self:
            self.app.currently_editing.finish_edit()
            
        self.editing = True
        if self.app:
            self.app.currently_editing = self
            
        self.entry.delete(0, "end")
        self.entry.insert(0, self.current_text)
        
        self.label.pack_forget()
        self.entry.pack(fill="both", expand=True, padx=2, pady=1)
        self.entry.focus_set()
        self.entry.select_range(0, "end")
        
    def finish_edit(self, event=None):
        if not self.editing:
            return
            
        new_text = self.entry.get().strip()
        if new_text and new_text != self.current_text:
            self.current_text = new_text
            self.label.configure(text=new_text)
            if self.callback:
                self.callback(new_text)
        
        self.cancel_edit()
        
    def cancel_edit(self, event=None):
        if not self.editing:
            return
            
        self.editing = False
        if self.app and self.app.currently_editing == self:
            self.app.currently_editing = None
            
        self.entry.pack_forget()
        self.label.pack(fill="both", expand=True)
        
    def get_text(self):
        return self.current_text
        
    def set_text(self, text):
        self.current_text = text
        self.label.configure(text=text)

class EpubCutterFinal:
    def __init__(self):
        self.root = TkinterDnD.Tk()
        self.root.title("EPUB Cutter")
        self.root.geometry("900x650")
        self.root.configure(bg="#1a1a1a")
        
        self.root.minsize(800, 500)
        
        # Нейтральная серо-голубая цветовая палитра
        self.colors = {
            "bg": "#1a1a1a",           # Основной фон
            "panel": "#2d2d2d",        # Фон панелей
            "element": "#3d3d3d",      # Фон элементов
            "accent": "#007acc",       # Голубой акцент
            "accent_hover": "#1e80c7", # Голубой при наведении
            "text": "#ffffff",         # Основной текст
            "text_dim": "#a3a3a3",     # Приглушенный текст
            "border": "#4a4a4a",       # Границы
            "success": "#6c7b7f",      # Нейтральный серый
            "warning": "#cc7a00",      # Оранжевый для предупреждений
            "danger": "#d14343"        # Красный для ошибок
        }
        
        self.fonts = {
            "title": get_safe_font(["Segoe UI", "Arial", "Helvetica"], 14, "bold"),
            "heading": get_safe_font(["Segoe UI", "Arial", "Helvetica"], 11, "bold"), 
            "body": get_safe_font(["Segoe UI", "Arial", "Helvetica"], 10, "normal"),
            "small": get_safe_font(["Segoe UI", "Arial", "Helvetica"], 9, "normal")
        }
        
        # Переменные
        self.epub_path = tk.StringVar()
        self.output_dir = tk.StringVar(value=os.getcwd())
        self.export_format = tk.StringVar(value="html")
        self.chapters = []
        self.chapter_vars = []
        self.chapter_widgets = []  # Для редактируемых названий
        self.images = {}
        self.progress_var = tk.DoubleVar()
        self.book_title = ""
        self.book_author = ""
        self.currently_editing = None  # Трекер текущего редактируемого элемента
        
        self.setup_ui()
        self.setup_drag_and_drop()
        
        # Горячие клавиши
        self.root.bind("<Control-o>", lambda e: self.browse_epub())
        self.root.bind("<Control-e>", lambda e: self.start_export())
        self.root.bind("<Control-a>", lambda e: self.select_all())
        self.root.bind("<Escape>", lambda e: self.deselect_all())
        
    def setup_ui(self):
        # Главный контейнер
        main_frame = tk.Frame(self.root, bg=self.colors["bg"])
        main_frame.pack(fill="both", expand=True, padx=8, pady=8)
        
        # Заголовок
        title_frame = tk.Frame(main_frame, bg=self.colors["bg"], height=35)
        title_frame.pack(fill="x", pady=(0, 8))
        title_frame.pack_propagate(False)
        
        title_label = tk.Label(title_frame, 
                              text="📚 EPUB Cutter", 
                              font=self.fonts["title"],
                              fg=self.colors["text"],
                              bg=self.colors["bg"])
        title_label.pack(side="left", anchor="w", pady=8)
        
        # Информация о книге (только название и автор) - жирный шрифт 14px
        self.book_info_label = tk.Label(title_frame,
                                       text="Книга не загружена",
                                       font=get_safe_font(["Segoe UI", "Arial", "Helvetica"], 12, "bold"),
                                       fg=self.colors["text_dim"],
                                       bg=self.colors["bg"])
        self.book_info_label.pack(side="right", anchor="e", pady=8)
        
        # Основная область - 2 колонки
        content_frame = tk.Frame(main_frame, bg=self.colors["bg"])
        content_frame.pack(fill="both", expand=True)
        
        # ЛЕВАЯ КОЛОНКА
        left_panel = tk.Frame(content_frame, bg=self.colors["panel"], width=450)
        left_panel.pack(side="left", fill="both", expand=True, padx=(0, 4))
        left_panel.pack_propagate(False)
        
        # Drag & Drop область
        self.drop_area = tk.Frame(left_panel, bg=self.colors["element"], height=50, relief="solid", bd=1)
        self.drop_area.pack(fill="x", padx=8, pady=8)
        self.drop_area.pack_propagate(False)
        
        drop_label = tk.Label(self.drop_area,
                             text="📁 Перетащите EPUB файл или нажмите для выбора",
                             font=self.fonts["small"],
                             fg=self.colors["text_dim"],
                             bg=self.colors["element"])
        drop_label.pack(expand=True)
        
        self.drop_area.bind("<Button-1>", lambda e: self.browse_epub())
        drop_label.bind("<Button-1>", lambda e: self.browse_epub())
        
        # Заголовок списка глав
        chapters_header = tk.Frame(left_panel, bg=self.colors["panel"], height=35)
        chapters_header.pack(fill="x", padx=8, pady=(0, 4))
        chapters_header.pack_propagate(False)
        
        tk.Label(chapters_header,
                text="Главы (клик - превью, двойной - переименование)",
                font=self.fonts["heading"],
                fg=self.colors["text"],
                bg=self.colors["panel"]).pack(side="left", pady=8)
        
        # Кнопки выбора
        buttons_frame = tk.Frame(chapters_header, bg=self.colors["panel"])
        buttons_frame.pack(side="right", pady=2)
        
        ModernButton(buttons_frame, "Все", command=self.select_all, style="success").pack(side="left", padx=(0, 2))
        ModernButton(buttons_frame, "Очистить", command=self.deselect_all, style="secondary").pack(side="left")
        
        # Контейнер для списка глав
        chapters_container = tk.Frame(left_panel, bg=self.colors["panel"])
        chapters_container.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        
        # Canvas для прокрутки
        self.chapters_canvas = tk.Canvas(chapters_container, 
                                        bg=self.colors["panel"],
                                        highlightthickness=0,
                                        bd=0)
        chapters_scrollbar = tk.Scrollbar(chapters_container, 
                                         orient="vertical", 
                                         command=self.chapters_canvas.yview,
                                         bg=self.colors["element"],
                                         troughcolor=self.colors["panel"])
        
        self.scrollable_chapters_frame = tk.Frame(self.chapters_canvas, bg=self.colors["panel"])
        
        self.scrollable_chapters_frame.bind(
            "<Configure>",
            lambda e: self.chapters_canvas.configure(scrollregion=self.chapters_canvas.bbox("all"))
        )
        
        self.chapters_canvas.create_window((0, 0), window=self.scrollable_chapters_frame, anchor="nw")
        self.chapters_canvas.configure(yscrollcommand=chapters_scrollbar.set)
        
        self.chapters_canvas.pack(side="left", fill="both", expand=True)
        chapters_scrollbar.pack(side="right", fill="y")
        
        # Улучшенная прокрутка колесом мыши
        self.chapters_canvas.bind("<MouseWheel>", self._on_mousewheel)
        self.scrollable_chapters_frame.bind("<MouseWheel>", self._on_mousewheel)
        # Привязка прокрутки ко всему контейнеру
        chapters_container.bind("<MouseWheel>", self._on_mousewheel)
        
        # ПРАВАЯ КОЛОНКА
        right_panel = tk.Frame(content_frame, bg=self.colors["panel"], width=350)
        right_panel.pack(side="right", fill="both", padx=(4, 0))
        right_panel.pack_propagate(False)
        
        # ВЕРХ - Настройки экспорта
        export_frame = tk.Frame(right_panel, bg=self.colors["element"], height=200)
        export_frame.pack(fill="x", padx=8, pady=8)
        export_frame.pack_propagate(False)
        
        tk.Label(export_frame,
                text="⚙️ Экспорт",
                font=self.fonts["heading"],
                fg=self.colors["text"],
                bg=self.colors["element"]).pack(anchor="w", padx=12, pady=8)
        
        # Формат
        format_frame = tk.Frame(export_frame, bg=self.colors["element"])
        format_frame.pack(fill="x", padx=12, pady=(0, 8))
        
        tk.Label(format_frame,
                text="Формат:",
                font=self.fonts["body"],
                fg=self.colors["text"],
                bg=self.colors["element"]).pack(anchor="w", pady=(0, 2))
        
        radio_frame = tk.Frame(format_frame, bg=self.colors["element"])
        radio_frame.pack(fill="x")
        
        tk.Radiobutton(radio_frame,
                      text="HTML главы",
                      variable=self.export_format,
                      value="html",
                      font=self.fonts["body"],
                      fg=self.colors["text"],
                      bg=self.colors["element"],
                      selectcolor=self.colors["accent"],
                      activebackground=self.colors["element"],
                      relief="flat").pack(side="left", padx=(0, 10))
        
        tk.Radiobutton(radio_frame,
                      text="EPUB главы",
                      variable=self.export_format,
                      value="epub",
                      font=self.fonts["body"],
                      fg=self.colors["text"],
                      bg=self.colors["element"],
                      selectcolor=self.colors["accent"],
                      activebackground=self.colors["element"],
                      relief="flat").pack(side="left", padx=(0, 10))
        
        tk.Radiobutton(radio_frame,
                      text="Веб-сайт",
                      variable=self.export_format,
                      value="website",
                      font=self.fonts["body"],
                      fg=self.colors["text"],
                      bg=self.colors["element"],
                      selectcolor=self.colors["accent"],
                      activebackground=self.colors["element"],
                      relief="flat").pack(side="left", padx=(0, 10))
        
        tk.Radiobutton(radio_frame,
                      text="Полная книга",
                      variable=self.export_format,
                      value="fullbook",
                      font=self.fonts["body"],
                      fg=self.colors["text"],
                      bg=self.colors["element"],
                      selectcolor=self.colors["accent"],
                      activebackground=self.colors["element"],
                      relief="flat").pack(side="left")
        
        # Папка для сохранения
        dir_frame = tk.Frame(export_frame, bg=self.colors["element"])
        dir_frame.pack(fill="x", padx=12, pady=(0, 8))
        
        tk.Label(dir_frame,
                text="Папка:",
                font=self.fonts["body"],
                fg=self.colors["text"],
                bg=self.colors["element"]).pack(anchor="w", pady=(0, 2))
        
        dir_input_frame = tk.Frame(dir_frame, bg=self.colors["element"])
        dir_input_frame.pack(fill="x")
        
        self.dir_entry = tk.Entry(dir_input_frame,
                                 textvariable=self.output_dir,
                                 font=self.fonts["small"],
                                 bg=self.colors["bg"],
                                 fg=self.colors["text"],
                                 relief="flat",
                                 bd=3)
        self.dir_entry.pack(side="left", fill="x", expand=True, padx=(0, 4))
        
        ModernButton(dir_input_frame, "...", command=self.browse_output_dir, style="secondary").pack(side="right")
        
        # Кнопка экспорта
        export_btn_frame = tk.Frame(export_frame, bg=self.colors["element"])
        export_btn_frame.pack(fill="x", padx=12, pady=8)
        
        self.export_button = ModernButton(export_btn_frame, 
                                         "🚀 Экспортировать", 
                                         command=self.start_export, 
                                         style="primary")
        self.export_button.pack()
        
        # НИЗ - Превью
        preview_frame = tk.Frame(right_panel, bg=self.colors["element"])
        preview_frame.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        
        tk.Label(preview_frame,
                text="👁 Превью главы",
                font=self.fonts["heading"],
                fg=self.colors["text"],
                bg=self.colors["element"]).pack(anchor="w", padx=12, pady=8)
        
        preview_container = tk.Frame(preview_frame, bg=self.colors["element"])
        preview_container.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        
        self.preview_text = scrolledtext.ScrolledText(
            preview_container,
            bg=self.colors["bg"],
            fg=self.colors["text"],
            font=self.fonts["small"],
            relief="flat",
            bd=0,
            padx=8,
            pady=8,
            wrap="word",
            state="disabled",
            height=8
        )
        self.preview_text.pack(fill="both", expand=True)
        
        # Строка состояния
        status_frame = tk.Frame(main_frame, bg=self.colors["element"], height=25)
        status_frame.pack(fill="x", pady=(8, 0))
        status_frame.pack_propagate(False)
        
        self.status_label = tk.Label(status_frame,
                                    text="Готов к работе",
                                    font=self.fonts["small"],
                                    fg=self.colors["text_dim"],
                                    bg=self.colors["element"])
        self.status_label.pack(side="left", padx=8, pady=4)
        
        self.progress_bar = ttk.Progressbar(status_frame,
                                           variable=self.progress_var,
                                           maximum=100,
                                           length=150)
        self.progress_bar.pack(side="right", padx=8, pady=4)
        
    def setup_drag_and_drop(self):
        self.drop_area.drop_target_register(DND_FILES)
        self.drop_area.dnd_bind('<<Drop>>', self.on_drop)
        
        self.drop_area.bind("<Enter>", lambda e: self.drop_area.configure(bg=self.colors["accent"]))
        self.drop_area.bind("<Leave>", lambda e: self.drop_area.configure(bg=self.colors["element"]))
        
    def on_drop(self, event):
        files = self.root.tk.splitlist(event.data)
        if files:
            file_path = files[0]
            if file_path.lower().endswith('.epub'):
                self.epub_path.set(file_path)
                self.load_epub_chapters()
            else:
                messagebox.showwarning("Предупреждение", "Пожалуйста, выберите EPUB файл")
        
        self.drop_area.configure(bg=self.colors["element"])
        
    def extract_book_metadata(self, opf_root):
        """Извлекает метаданные книги из OPF"""
        try:
            # Поиск названия книги - пробуем разные варианты
            title_elem = opf_root.find('.//{http://purl.org/dc/elements/1.1/}title')
            if title_elem is not None and title_elem.text:
                self.book_title = title_elem.text.strip()
            else:
                # Альтернативный поиск без namespace
                title_elem = opf_root.find('.//title')
                self.book_title = title_elem.text.strip() if title_elem is not None and title_elem.text else "Без названия"
            
            # Поиск автора - пробуем разные варианты
            creator_elem = opf_root.find('.//{http://purl.org/dc/elements/1.1/}creator')
            if creator_elem is not None and creator_elem.text:
                self.book_author = creator_elem.text.strip()
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
                            self.book_author = author_elem.text.strip()
                            break
                    except:
                        continue
                else:
                    self.book_author = "Автор неизвестен"
            
            # Очистка от лишних символов
            if self.book_title and len(self.book_title) > 100:
                self.book_title = self.book_title[:97] + "..."
                
            if self.book_author and len(self.book_author) > 80:
                self.book_author = self.book_author[:77] + "..."
            
        except Exception as e:
            print(f"Ошибка извлечения метаданных: {e}")
            self.book_title = "Без названия"
            self.book_author = "Автор неизвестен"
            
    def update_book_info(self):
        """Обновляет информацию о книге в интерфейсе"""
        info_text = f'"{self.book_title}" — {self.book_author}'
        self.book_info_label.configure(text=info_text, fg=self.colors["accent"])
        
    def _on_mousewheel(self, event):
        self.chapters_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
    def browse_epub(self):
        filename = filedialog.askopenfilename(
            title="Выберите EPUB файл",
            filetypes=[("EPUB files", "*.epub"), ("All files", "*.*")]
        )
        if filename:
            self.epub_path.set(filename)
            self.load_epub_chapters()
            
    def browse_output_dir(self):
        dirname = filedialog.askdirectory(title="Выберите папку для сохранения")
        if dirname:
            self.output_dir.set(dirname)
            
    def update_status(self, text, color=None):
        self.status_label.configure(text=text)
        if color:
            self.status_label.configure(fg=self.colors.get(color, self.colors["text_dim"]))
            
    def load_epub_chapters(self):
        try:
            self.update_status("Загрузка...", "warning")
            
            # Очистка
            for widget in self.scrollable_chapters_frame.winfo_children():
                widget.destroy()
            self.chapters.clear()
            self.chapter_vars.clear()
            self.chapter_widgets.clear()
            self.images.clear()
            self.currently_editing = None  # Сброс редактирования
            
            # Очистка превью
            self.preview_text.configure(state="normal")
            self.preview_text.delete(1.0, "end")
            self.preview_text.insert("end", "Выберите главу для просмотра")
            self.preview_text.configure(state="disabled")
            
            with zipfile.ZipFile(self.epub_path.get(), 'r') as epub_zip:
                # Чтение структуры EPUB
                container_xml = epub_zip.read('META-INF/container.xml')
                container_root = ET.fromstring(container_xml)
                
                opf_path = container_root.find('.//{urn:oasis:names:tc:opendocument:xmlns:container}rootfile').get('full-path')
                opf_content = epub_zip.read(opf_path)
                opf_root = ET.fromstring(opf_content)
                
                # Извлечение метаданных книги
                self.extract_book_metadata(opf_root)
                
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
                                
                                title = re.sub(r'[<>:"/\\|?*]', '', title)
                                
                                self.chapters.append({
                                    'title': title,
                                    'file_path': file_path,
                                    'content': chapter_content
                                })
                                
                            except Exception as e:
                                print(f"Ошибка при чтении главы {file_path}: {e}")
                                continue
                
                # Создание интерфейса для глав
                self.create_chapter_checkboxes()
                
            self.update_status(f"Загружено {len(self.chapters)} глав", "success")
            self.update_book_info()
            
        except Exception as e:
            self.update_status(f"Ошибка: {str(e)}", "danger")
            messagebox.showerror("Ошибка", f"Не удалось открыть EPUB файл: {e}")
            
    def on_chapter_title_changed(self, index, new_title):
        """Обработчик изменения названия главы"""
        if 0 <= index < len(self.chapters):
            self.chapters[index]['title'] = new_title
            self.update_status(f"Переименована глава {index+1}", "success")
            
    def create_chapter_checkboxes(self):
        """Создание редактируемых чекбоксов для глав"""
        for i, chapter in enumerate(self.chapters):
            var = tk.BooleanVar()
            self.chapter_vars.append(var)
            
            # Контейнер для чекбокса и редактируемого названия
            container = tk.Frame(self.scrollable_chapters_frame, bg=self.colors["panel"])
            container.pack(fill="x", padx=4, pady=1)
            
            # Чекбокс
            checkbox = tk.Checkbutton(
                container,
                variable=var,
                bg=self.colors["panel"],
                fg=self.colors["text"],
                selectcolor=self.colors["accent"],
                activebackground=self.colors["panel"],
                relief="flat",
                bd=0
            )
            checkbox.pack(side="left", padx=2)
            
            # Редактируемое название главы - выровнено по левому краю
            title_text = f"{i+1:02d}. {chapter['title'][:40]}{'...' if len(chapter['title']) > 40 else ''}"
            editable_title = EditableLabel(
                container,
                text=title_text,
                callback=lambda new_title, idx=i: self.on_chapter_title_changed(idx, new_title),
                app_instance=self,
                bg=self.colors["panel"]
            )
            editable_title.pack(side="left", fill="x", expand=True, padx=2, anchor="w")
            
            # Привязка событий для одиночного и двойного клика
            def on_single_click(event, idx=i):
                # Завершить текущее редактирование при клике на другую главу
                if self.currently_editing:
                    self.currently_editing.finish_edit()
                self.show_chapter_preview(idx)
                
            def on_double_click(event, title_widget=editable_title):
                title_widget.start_edit()
                
            # Привязываем события к контейнеру и названию
            container.bind("<Button-1>", on_single_click)
            editable_title.bind("<Button-1>", on_single_click)
            editable_title.label.bind("<Button-1>", on_single_click)
            editable_title.bind("<Double-Button-1>", on_double_click)
            editable_title.label.bind("<Double-Button-1>", on_double_click)
            
            self.chapter_widgets.append({
                'container': container,
                'checkbox': checkbox,
                'title': editable_title
            })
            
            # Hover эффект для контейнера
            def on_enter(e, c=container):
                c.configure(bg=self.colors["element"])
                for child in c.winfo_children():
                    if hasattr(child, 'configure'):
                        try:
                            child.configure(bg=self.colors["element"])
                        except:
                            pass
                        if hasattr(child, 'bg_color'):
                            child.bg_color = self.colors["element"]
                            if hasattr(child, 'label'):
                                child.label.configure(bg=self.colors["element"])
                            
            def on_leave(e, c=container):
                c.configure(bg=self.colors["panel"])
                for child in c.winfo_children():
                    if hasattr(child, 'configure'):
                        try:
                            child.configure(bg=self.colors["panel"])
                        except:
                            pass
                        if hasattr(child, 'bg_color'):
                            child.bg_color = self.colors["panel"]
                            if hasattr(child, 'label'):
                                child.label.configure(bg=self.colors["panel"])
                            
            container.bind("<Enter>", on_enter)
            container.bind("<Leave>", on_leave)
            checkbox.bind("<Enter>", on_enter)
            checkbox.bind("<Leave>", on_leave)
            editable_title.bind("<Enter>", on_enter)
            editable_title.bind("<Leave>", on_leave)
            
            # Привязка прокрутки к каждому элементу
            container.bind("<MouseWheel>", self._on_mousewheel)
            checkbox.bind("<MouseWheel>", self._on_mousewheel)
            editable_title.bind("<MouseWheel>", self._on_mousewheel)
            editable_title.label.bind("<MouseWheel>", self._on_mousewheel)
            
    def show_chapter_preview(self, chapter_index):
        """Показ превью главы"""
        if 0 <= chapter_index < len(self.chapters):
            chapter = self.chapters[chapter_index]
            
            try:
                content = chapter['content'].decode('utf-8')
                
                text_content = re.sub(r'<[^>]+>', '', content)
                text_content = re.sub(r'\s+', ' ', text_content).strip()
                
                self.preview_text.configure(state="normal")
                self.preview_text.delete(1.0, "end")
                
                self.preview_text.insert("end", f"{chapter['title']}\n\n", "title")
                
                preview_text = text_content[:800]
                if len(text_content) > 800:
                    preview_text += "\n\n..."
                    
                self.preview_text.insert("end", preview_text)
                
                self.preview_text.tag_configure("title", font=self.fonts["heading"], foreground=self.colors["accent"])
                
                self.preview_text.configure(state="disabled")
                self.preview_text.see(1.0)
                
            except Exception as e:
                self.preview_text.configure(state="normal")
                self.preview_text.delete(1.0, "end")
                self.preview_text.insert("end", f"Ошибка: {e}")
                self.preview_text.configure(state="disabled")
                
    def select_all(self):
        for var in self.chapter_vars:
            var.set(True)
        self.update_status(f"Выбраны все главы ({len(self.chapter_vars)})", "success")
        
    def deselect_all(self):
        for var in self.chapter_vars:
            var.set(False)
        self.update_status("Выбор снят", "text_dim")
        
    def start_export(self):
        if not self.chapters:
            messagebox.showwarning("Предупреждение", "Сначала загрузите EPUB файл")
            return
            
        selected_chapters = [
            (i, chapter) for i, (chapter, var) in enumerate(zip(self.chapters, self.chapter_vars))
            if var.get()
        ]
        
        if not selected_chapters:
            messagebox.showwarning("Предупреждение", "Выберите хотя бы одну главу")
            return
        
        self.export_button.btn.configure(text="⏳ Экспорт...")
        threading.Thread(target=self.export_chapters_thread, args=(selected_chapters,), daemon=True).start()
    
    def create_website_css(self):
        """Создает CSS стили для веб-сайта книги"""
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
    
    def generate_index_html(self, selected_chapters, output_path):
        """Генерирует index.html с оглавлением"""
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
        
        html_content += """        </ul>
    </div>
    
    <div class="navigation">
        <p>Эта книга содержит """ + str(len(selected_chapters)) + """ глав. Выберите главу из оглавления выше для чтения.</p>
    </div>
</body>
</html>"""
        
        # Сохранение index.html
        with open(output_path / "index.html", 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        # Сохранение CSS
        with open(output_path / "styles.css", 'w', encoding='utf-8') as f:
            f.write(self.create_website_css())
    
    def export_as_website(self, selected_chapters, output_path):
        """Экспортирует книгу как веб-сайт с оглавлением"""
        # Создание главной папки сайта
        site_name = f"{re.sub(r'[<>:\"/\\|?*]', '', self.book_title)}_website"
        site_path = output_path / site_name
        site_path.mkdir(parents=True, exist_ok=True)
        
        # Создание папки для изображений
        images_path = site_path / "images"
        images_path.mkdir(exist_ok=True)
        
        # Генерация index.html с оглавлением
        self.generate_index_html(selected_chapters, site_path)
        
        total_chapters = len(selected_chapters)
        
        # Экспорт каждой главы как HTML с навигацией
        for idx, (i, chapter) in enumerate(selected_chapters):
            progress = (idx / total_chapters) * 100
            self.root.after(0, lambda p=progress: self.progress_var.set(p))
            self.root.after(0, lambda: self.update_status(f"Создание сайта: глава {idx + 1}/{total_chapters}...", "warning"))
            
            chapter_num = i + 1
            safe_title = re.sub(r'[<>:"/\\|?*]', '', chapter['title'])
            filename = f"chapter_{chapter_num:02d}_{safe_title}.html"
            filepath = site_path / filename
            
            # Обработка содержимого главы
            content = chapter['content'].decode('utf-8')
            content = content.replace('xmlns="http://www.w3.org/1999/xhtml"', '')
            
            # Обработка изображений
            content = self.process_images_for_website(content, images_path)
            
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
        
        return site_path
    
    def process_images_for_website(self, content, images_path):
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
    
    def create_full_book_epub(self, selected_chapters, output_path):
        """Создает полную книгу EPUB с оглавлением и навигацией"""
        book_name = f"{re.sub(r'[<>:\"/\\|?*]', '', self.book_title)}_complete"
        epub_path = output_path / f"{book_name}.epub"
        
        with zipfile.ZipFile(epub_path, 'w', zipfile.ZIP_DEFLATED) as epub_zip:
            # mimetype
            epub_zip.writestr('mimetype', 'application/epub+zip', compress_type=zipfile.ZIP_STORED)
            
            # META-INF/container.xml
            container_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>'''
            epub_zip.writestr('META-INF/container.xml', container_xml)
            
            # Собираем все изображения, используемые в выбранных главах
            all_used_images = {}
            for chapter_idx, chapter in selected_chapters:
                chapter_content = chapter['content'].decode('utf-8')
                chapter_images = self.get_chapter_images(chapter_content)
                all_used_images.update(chapter_images)
            
            # Создаем манифест со всеми главами и изображениями
            manifest_items = []
            
            # Добавляем оглавление
            manifest_items.append('    <item id="toc" href="toc.xhtml" media-type="application/xhtml+xml"/>')
            
            # Добавляем главы
            for idx, (chapter_idx, chapter) in enumerate(selected_chapters):
                chapter_id = f"chapter{idx+1:02d}"
                chapter_file = f"chapter{idx+1:02d}.xhtml"
                manifest_items.append(f'    <item id="{chapter_id}" href="{chapter_file}" media-type="application/xhtml+xml"/>')
            
            # Добавляем изображения
            for i, (img_path, img_data) in enumerate(all_used_images.items()):
                img_filename = os.path.basename(img_path)
                img_id = f"img{i+1:03d}"
                media_type = self.get_image_media_type(img_filename)
                manifest_items.append(f'    <item id="{img_id}" href="images/{img_filename}" media-type="{media_type}"/>')
                
                # Сохраняем изображение
                epub_zip.writestr(f'OEBPS/images/{img_filename}', img_data)
            
            # Создаем spine (порядок чтения)
            spine_items = ['    <itemref idref="toc"/>']
            for idx, (chapter_idx, chapter) in enumerate(selected_chapters):
                chapter_id = f"chapter{idx+1:02d}"
                spine_items.append(f'    <itemref idref="{chapter_id}"/>')
            
            # OEBPS/content.opf
            manifest_str = '\n'.join(manifest_items)
            spine_str = '\n'.join(spine_items)
            
            content_opf = f'''<?xml version="1.0" encoding="UTF-8"?>
<package version="3.0" xmlns="http://www.idpf.org/2007/opf" unique-identifier="BookId">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:identifier id="BookId">{book_name}</dc:identifier>
    <dc:title>{html.escape(self.book_title)}</dc:title>
    <dc:creator>{html.escape(self.book_author)}</dc:creator>
    <dc:language>ru</dc:language>
    <meta property="dcterms:modified">2024-01-01T00:00:00Z</meta>
  </metadata>
  <manifest>
{manifest_str}
  </manifest>
  <spine>
{spine_str}
  </spine>
</package>'''
            epub_zip.writestr('OEBPS/content.opf', content_opf)
            
            # Создаем оглавление (toc.xhtml)
            toc_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
    <title>Содержание</title>
    <style>
        body {{ font-family: Georgia, serif; margin: 2em; }}
        .toc-header {{ text-align: center; margin-bottom: 2em; }}
        .book-title {{ font-size: 2em; color: #333; margin-bottom: 0.5em; }}
        .book-author {{ font-size: 1.2em; color: #666; font-style: italic; }}
        .toc-list {{ list-style: none; padding: 0; }}
        .toc-item {{ margin: 1em 0; padding: 0.8em; border-left: 3px solid #007acc; background: #f8f9fa; }}
        .toc-link {{ text-decoration: none; color: #333; font-weight: bold; }}
        .toc-link:hover {{ color: #007acc; }}
        .chapter-number {{ color: #007acc; margin-right: 1em; }}
    </style>
</head>
<body>
    <div class="toc-header">
        <h1 class="book-title">{html.escape(self.book_title)}</h1>
        <p class="book-author">{html.escape(self.book_author)}</p>
    </div>
    
    <nav>
        <h2>📚 Содержание</h2>
        <ol class="toc-list">
'''
            
            for idx, (chapter_idx, chapter) in enumerate(selected_chapters):
                chapter_file = f"chapter{idx+1:02d}.xhtml"
                chapter_num = chapter_idx + 1
                toc_content += f'''            <li class="toc-item">
                <a href="{chapter_file}" class="toc-link">
                    <span class="chapter-number">Глава {chapter_num}</span>
                    {html.escape(chapter['title'])}
                </a>
            </li>
'''
            
            toc_content += '''        </ol>
    </nav>
</body>
</html>'''
            
            epub_zip.writestr('OEBPS/toc.xhtml', toc_content.encode('utf-8'))
            
            # Создаем файлы глав
            total_chapters = len(selected_chapters)
            for idx, (chapter_idx, chapter) in enumerate(selected_chapters):
                progress = (idx / total_chapters) * 100
                self.root.after(0, lambda p=progress: self.progress_var.set(p))
                self.root.after(0, lambda: self.update_status(f"Создание книги: глава {idx + 1}/{total_chapters}...", "warning"))
                
                chapter_file = f"chapter{idx+1:02d}.xhtml"
                chapter_content = chapter['content'].decode('utf-8')
                
                # Обработка изображений для EPUB
                processed_content = self.process_images_for_epub(chapter_content, all_used_images)
                
                # Добавляем навигацию в главу
                prev_link = ""
                next_link = ""
                
                if idx > 0:
                    prev_file = f"chapter{idx:02d}.xhtml"
                    prev_link = f'<p><a href="{prev_file}">← Предыдущая глава</a></p>'
                else:
                    prev_link = '<p><a href="toc.xhtml">← К содержанию</a></p>'
                
                if idx < len(selected_chapters) - 1:
                    next_file = f"chapter{idx+2:02d}.xhtml"
                    next_link = f'<p><a href="{next_file}">Следующая глава →</a></p>'
                else:
                    next_link = '<p><a href="toc.xhtml">К содержанию →</a></p>'
                
                # Вставляем навигацию в начало и конец главы
                body_start = processed_content.find('<body')
                if body_start != -1:
                    body_end = processed_content.find('>', body_start) + 1
                    navigation = f'''
    <div style="text-align: center; margin-bottom: 2em; padding-bottom: 1em; border-bottom: 1px solid #eee;">
        <a href="toc.xhtml" style="margin: 0 1em;">📚 Содержание</a>
        {prev_link.replace('<p>', '').replace('</p>', '')}
        {next_link.replace('<p>', '').replace('</p>', '')}
    </div>
'''
                    processed_content = processed_content[:body_end] + navigation + processed_content[body_end:]
                    
                    # Добавляем навигацию в конец
                    body_close = processed_content.rfind('</body>')
                    if body_close != -1:
                        end_navigation = f'''
    <div style="text-align: center; margin-top: 2em; padding-top: 1em; border-top: 1px solid #eee;">
        <a href="toc.xhtml" style="margin: 0 1em;">📚 Содержание</a>
        {prev_link.replace('<p>', '').replace('</p>', '')}
        {next_link.replace('<p>', '').replace('</p>', '')}
    </div>
'''
                        processed_content = processed_content[:body_close] + end_navigation + processed_content[body_close:]
                
                epub_zip.writestr(f'OEBPS/{chapter_file}', processed_content.encode('utf-8'))
        
        return epub_path
        
    def export_chapters_thread(self, selected_chapters):
        try:
            output_path = Path(self.output_dir.get())
            output_path.mkdir(parents=True, exist_ok=True)
            
            if self.export_format.get() == "website":
                # Экспорт как веб-сайт
                site_path = self.export_as_website(selected_chapters, output_path)
                self.root.after(0, lambda: self.progress_var.set(100))
                self.root.after(0, lambda: self.update_status(f"✅ Сайт создан: {site_path.name}", "success"))
                self.root.after(0, lambda: messagebox.showinfo("Успех", f"Веб-сайт книги создан в папке:\n{site_path}"))
                
            elif self.export_format.get() == "fullbook":
                # Экспорт как полная книга EPUB
                book_path = self.create_full_book_epub(selected_chapters, output_path)
                self.root.after(0, lambda: self.progress_var.set(100))
                self.root.after(0, lambda: self.update_status(f"✅ Книга создана: {book_path.name}", "success"))
                self.root.after(0, lambda: messagebox.showinfo("Успех", f"Полная книга EPUB создана:\n{book_path}"))
                
            else:
                # Стандартный экспорт отдельными файлами
                total_chapters = len(selected_chapters)
                
                for idx, (i, chapter) in enumerate(selected_chapters):
                    progress = (idx / total_chapters) * 100
                    self.root.after(0, lambda p=progress: self.progress_var.set(p))
                    self.root.after(0, lambda: self.update_status(f"Экспорт {idx + 1}/{total_chapters}...", "warning"))
                    
                    chapter_num = i + 1
                    safe_title = re.sub(r'[<>:"/\\|?*]', '', chapter['title'])
                    
                    if self.export_format.get() == "html":
                        filename = f"{chapter_num:02d}_{safe_title}.html"
                        filepath = output_path / filename
                        
                        content = chapter['content'].decode('utf-8')
                        content = content.replace('xmlns="http://www.w3.org/1999/xhtml"', '')
                        
                        img_folder = output_path / f"{chapter_num:02d}_{safe_title}_images"
                        img_folder.mkdir(exist_ok=True)
                        
                        content = self.process_images_for_html(content, img_folder, chapter_num)
                        
                        with open(filepath, 'w', encoding='utf-8') as f:
                            f.write(content)
                            
                    else:  # epub
                        filename = f"{chapter_num:02d}_{safe_title}.epub"
                        filepath = output_path / filename
                        
                        self.create_single_chapter_epub(filepath, chapter, chapter_num)
                
                self.root.after(0, lambda: self.progress_var.set(100))
                self.root.after(0, lambda: self.update_status(f"✅ Готово! {total_chapters} глав", "success"))
                self.root.after(0, lambda: messagebox.showinfo("Успех", f"Экспортировано {total_chapters} глав"))
            
        except Exception as e:
            self.root.after(0, lambda: self.update_status(f"❌ Ошибка: {str(e)}", "danger"))
            self.root.after(0, lambda: messagebox.showerror("Ошибка", f"Ошибка при экспорте: {e}"))
        finally:
            self.root.after(0, lambda: self.export_button.btn.configure(text="🚀 Экспортировать"))
            self.root.after(0, lambda: self.progress_var.set(0))
    
    # Остальные методы такие же, как в предыдущей версии
    def process_images_for_html(self, content, img_folder, chapter_num):
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
                    img_filepath = img_folder / img_filename
                    
                    with open(img_filepath, 'wb') as f:
                        f.write(img_data)
                    
                    relative_path = f"./{img_folder.name}/{img_filename}"
                    new_img_tag = img_tag.replace(f'src="{src}"', f'src="{relative_path}"')
                    new_img_tag = new_img_tag.replace(f"src='{src}'", f'src="{relative_path}"')
                    return new_img_tag
                    
            return img_tag
        
        return re.sub(img_pattern, replace_img, content)
            
    def create_single_chapter_epub(self, filepath, chapter, chapter_num):
        with zipfile.ZipFile(filepath, 'w', zipfile.ZIP_DEFLATED) as epub_zip:
            epub_zip.writestr('mimetype', 'application/epub+zip', compress_type=zipfile.ZIP_STORED)
            
            container_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>'''
            epub_zip.writestr('META-INF/container.xml', container_xml)
            
            chapter_content = chapter['content'].decode('utf-8')
            used_images = self.get_chapter_images(chapter_content)
            
            manifest_items = ['    <item id="chapter" href="chapter.xhtml" media-type="application/xhtml+xml"/>']
            
            for i, (img_path, img_data) in enumerate(used_images.items()):
                img_filename = os.path.basename(img_path)
                img_id = f"img{i+1}"
                media_type = self.get_image_media_type(img_filename)
                manifest_items.append(f'    <item id="{img_id}" href="images/{img_filename}" media-type="{media_type}"/>')
                
                epub_zip.writestr(f'OEBPS/images/{img_filename}', img_data)
            
            manifest_str = '\n'.join(manifest_items)
            content_opf = f'''<?xml version="1.0" encoding="UTF-8"?>
<package version="3.0" xmlns="http://www.idpf.org/2007/opf" unique-identifier="BookId">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:identifier id="BookId">{chapter_num}</dc:identifier>
    <dc:title>{html.escape(chapter['title'])}</dc:title>
    <dc:language>ru</dc:language>
  </metadata>
  <manifest>
{manifest_str}
  </manifest>
  <spine>
    <itemref idref="chapter"/>
  </spine>
</package>'''
            epub_zip.writestr('OEBPS/content.opf', content_opf)
            
            processed_content = self.process_images_for_epub(chapter_content, used_images)
            epub_zip.writestr('OEBPS/chapter.xhtml', processed_content.encode('utf-8'))
    
    def get_chapter_images(self, content):
        import re
        used_images = {}
        
        img_pattern = r'<img[^>]*src=["\']([^"\']+)["\'][^>]*>'
        matches = re.findall(img_pattern, content)
        
        for src in matches:
            # Очищаем путь от относительных ссылок и нормализуем
            src_clean = src.replace('../', '').replace('./', '')
            
            # Ищем изображение по точному совпадению имени файла
            for img_path, img_data in self.images.items():
                img_filename = os.path.basename(img_path)
                src_filename = os.path.basename(src_clean)
                
                # Сравниваем имена файлов
                if img_filename == src_filename:
                    used_images[img_path] = img_data
                    break
                    
        return used_images
    
    def get_image_media_type(self, filename):
        ext = os.path.splitext(filename)[1].lower()
        mime_types = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.svg': 'image/svg+xml',
            '.bmp': 'image/bmp',
            '.webp': 'image/webp'
        }
        return mime_types.get(ext, 'image/jpeg')
    
    def process_images_for_epub(self, content, used_images):
        import re
        
        def replace_img(match):
            img_tag = match.group(0)
            src = match.group(1)
            src_clean = src.replace('../', '').replace('./', '')
            
            # Ищем изображение по имени файла
            for img_path in used_images.keys():
                img_filename = os.path.basename(img_path)
                src_filename = os.path.basename(src_clean)
                
                if img_filename == src_filename:
                    new_src = f"images/{img_filename}"
                    new_img_tag = img_tag.replace(f'src="{src}"', f'src="{new_src}"')
                    new_img_tag = new_img_tag.replace(f"src='{src}'", f'src="{new_src}"')
                    return new_img_tag
                    
            return img_tag
        
        img_pattern = r'<img[^>]*src=["\']([^"\']+)["\'][^>]*>'
        return re.sub(img_pattern, replace_img, content)
            
    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = EpubCutterFinal()
    app.run()