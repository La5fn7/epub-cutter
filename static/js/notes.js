// Система заметок для EPUB Cutter
class NotesSystem {
    constructor() {
        this.bookId = null;
        this.chapterTitle = null;
        this.init();
    }

    init() {
        // Получаем bookId и название главы из URL или метаданных страницы
        this.extractPageInfo();
        
        // Добавляем обработчики событий
        this.setupEventListeners();
        
        // Создаем элементы интерфейса
        this.createNoteInterface();
    }

    extractPageInfo() {
        // Пытаемся получить bookId из URL
        const pathParts = window.location.pathname.split('/');
        if (pathParts.includes('book') && pathParts.length >= 3) {
            // URL вида /book/{book_path}/{filename}
            this.bookPath = pathParts[2];
            
            // Получаем название главы из заголовка страницы
            const titleElement = document.querySelector('title');
            if (titleElement) {
                const fullTitle = titleElement.textContent;
                // Извлекаем название главы (до первого ' - ')
                this.chapterTitle = fullTitle.split(' - ')[0] || 'Неизвестная глава';
            }
            
            // Получаем bookId из данных на странице или делаем запрос
            this.getBookIdFromPath();
        }
    }

    async getBookIdFromPath() {
        // Этот метод должен получить bookId по bookPath
        // Пока используем простое решение - извлекаем из localStorage или делаем запрос
        try {
            const response = await fetch(`/api/book-info?path=${encodeURIComponent(this.bookPath)}`);
            if (response.ok) {
                const data = await response.json();
                this.bookId = data.book_id;
            }
        } catch (error) {
            console.log('Не удалось получить book_id:', error);
            // Используем временное решение - ищем в localStorage
            this.bookId = localStorage.getItem('currentBookId');
        }
    }

    setupEventListeners() {
        // Обработка выделения текста
        document.addEventListener('mouseup', (e) => {
            this.handleTextSelection(e);
        });

        // Обработка клавиш
        document.addEventListener('keydown', (e) => {
            if (e.ctrlKey && e.key === 's') {
                e.preventDefault();
                this.saveSelectedText();
            }
        });
    }

    handleTextSelection(event) {
        const selection = window.getSelection();
        const selectedText = selection.toString().trim();

        if (selectedText.length > 0) {
            // Показываем кнопку для сохранения заметки
            this.showNoteButton(event, selectedText, selection);
        } else {
            // Скрываем кнопку
            this.hideNoteButton();
        }
    }

    showNoteButton(event, selectedText, selection) {
        // Удаляем существующую кнопку, если есть
        this.hideNoteButton();

        // Создаем кнопку
        const button = document.createElement('div');
        button.id = 'note-save-button';
        button.className = 'note-save-button';
        button.innerHTML = `
            <button onclick="notesSystem.saveQuote('${this.escapeHtml(selectedText)}')">
                📝 Сохранить в заметки
            </button>
        `;

        // Позиционируем кнопку рядом с выделенным текстом
        const rect = selection.getRangeAt(0).getBoundingClientRect();
        button.style.position = 'absolute';
        button.style.left = `${rect.left + window.scrollX}px`;
        button.style.top = `${rect.bottom + window.scrollY + 5}px`;
        button.style.zIndex = '1000';

        document.body.appendChild(button);

        // Автоматически скрываем через 5 секунд
        setTimeout(() => {
            this.hideNoteButton();
        }, 5000);
    }

    hideNoteButton() {
        const existingButton = document.getElementById('note-save-button');
        if (existingButton) {
            existingButton.remove();
        }
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML.replace(/'/g, '&#39;');
    }

    async saveQuote(selectedText) {
        if (!this.bookId) {
            alert('Не удалось определить книгу. Попробуйте перезагрузить страницу.');
            return;
        }

        try {
            const response = await fetch('/api/notes', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    book_id: this.bookId,
                    chapter_title: this.chapterTitle,
                    selected_text: selectedText,
                    note_text: ''
                })
            });

            const data = await response.json();
            
            if (data.success) {
                this.showSuccessMessage();
                this.hideNoteButton();
                
                // Очищаем выделение
                window.getSelection().removeAllRanges();
            } else {
                alert('Ошибка при сохранении заметки: ' + data.error);
            }
        } catch (error) {
            console.error('Error saving note:', error);
            alert('Ошибка при сохранении заметки');
        }
    }

    showSuccessMessage() {
        // Создаем уведомление об успешном сохранении
        const notification = document.createElement('div');
        notification.className = 'note-success-notification';
        notification.textContent = '✅ Заметка сохранена!';
        notification.style.position = 'fixed';
        notification.style.top = '20px';
        notification.style.right = '20px';
        notification.style.backgroundColor = '#4CAF50';
        notification.style.color = 'white';
        notification.style.padding = '10px 20px';
        notification.style.borderRadius = '5px';
        notification.style.zIndex = '1001';
        notification.style.boxShadow = '0 2px 10px rgba(0,0,0,0.3)';

        document.body.appendChild(notification);

        // Удаляем уведомление через 3 секунды
        setTimeout(() => {
            notification.remove();
        }, 3000);
    }

    createNoteInterface() {
        // Добавляем кнопку "Заметки" в навигацию, если её ещё нет
        this.addNotesButtonToNavigation();
    }

    addNotesButtonToNavigation() {
        const navigation = document.querySelector('.navigation');
        if (navigation && !document.querySelector('.notes-nav-button')) {
            const notesButton = document.createElement('a');
            notesButton.href = `/notes/${this.bookId}`;
            notesButton.className = 'nav-button notes-nav-button';
            notesButton.innerHTML = '📝 Заметки';
            notesButton.target = '_blank'; // Открываем в новой вкладке
            
            navigation.appendChild(notesButton);
        }
    }
}

// Инициализируем систему заметок при загрузке страницы
let notesSystem;
document.addEventListener('DOMContentLoaded', function() {
    notesSystem = new NotesSystem();
});

// Функция для установки bookId извне (может быть вызвана из шаблона)
function setBookId(bookId) {
    if (window.notesSystem) {
        window.notesSystem.bookId = bookId;
    } else {
        localStorage.setItem('currentBookId', bookId);
    }
}