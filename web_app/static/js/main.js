// Основной JavaScript для EPUB Cutter Web

document.addEventListener('DOMContentLoaded', function() {
    // Инициализация приложения
    initializeApp();
});

function initializeApp() {
    // Добавляем обработчики событий
    setupGlobalEventListeners();
    
    // Проверяем поддержку drag & drop
    if (!isDragAndDropSupported()) {
        console.warn('Drag & Drop не поддерживается в этом браузере');
    }
}

function setupGlobalEventListeners() {
    // Предотвращаем случайное перетаскивание файлов на страницу
    document.addEventListener('dragover', function(e) {
        e.preventDefault();
        e.stopPropagation();
    });
    
    document.addEventListener('drop', function(e) {
        e.preventDefault();
        e.stopPropagation();
    });
    
    // Обработка клавиш
    document.addEventListener('keydown', function(e) {
        // ESC для закрытия модальных окон
        if (e.key === 'Escape') {
            closeAllModals();
        }
    });
}

function isDragAndDropSupported() {
    const div = document.createElement('div');
    return (('draggable' in div) || ('ondragstart' in div && 'ondrop' in div)) && 
           'FormData' in window && 
           'FileReader' in window;
}

function closeAllModals() {
    const modals = document.querySelectorAll('.modal');
    modals.forEach(modal => {
        modal.style.display = 'none';
    });
}

// Утилиты для работы с API
class ApiClient {
    static async uploadFile(file, onProgress) {
        return new Promise((resolve, reject) => {
            const formData = new FormData();
            formData.append('file', file);
            
            const xhr = new XMLHttpRequest();
            
            // Обработка прогресса загрузки
            if (onProgress) {
                xhr.upload.addEventListener('progress', (e) => {
                    if (e.lengthComputable) {
                        const percentComplete = (e.loaded / e.total) * 100;
                        onProgress(percentComplete);
                    }
                });
            }
            
            xhr.addEventListener('load', () => {
                if (xhr.status === 200) {
                    try {
                        const response = JSON.parse(xhr.responseText);
                        resolve(response);
                    } catch (e) {
                        reject(new Error('Ошибка парсинга ответа сервера'));
                    }
                } else {
                    reject(new Error(`HTTP ${xhr.status}: ${xhr.statusText}`));
                }
            });
            
            xhr.addEventListener('error', () => {
                reject(new Error('Сетевая ошибка при загрузке'));
            });
            
            xhr.addEventListener('timeout', () => {
                reject(new Error('Превышено время ожидания'));
            });
            
            xhr.timeout = 300000; // 5 минут
            xhr.open('POST', '/upload');
            xhr.send(formData);
        });
    }
    
    static async deleteBook(bookId) {
        const response = await fetch(`/delete/${bookId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        return await response.json();
    }
}

// Утилиты для валидации файлов
class FileValidator {
    static validateEpubFile(file) {
        const errors = [];
        
        // Проверка расширения
        if (!file.name.toLowerCase().endsWith('.epub')) {
            errors.push('Недопустимый формат файла. Поддерживается только EPUB.');
        }
        
        // Проверка размера (100 МБ)
        const maxSize = 100 * 1024 * 1024;
        if (file.size > maxSize) {
            errors.push(`Файл слишком большой. Максимальный размер: ${this.formatFileSize(maxSize)}.`);
        }
        
        // Проверка на пустой файл
        if (file.size === 0) {
            errors.push('Файл пуст.');
        }
        
        return {
            isValid: errors.length === 0,
            errors: errors
        };
    }
    
    static formatFileSize(bytes) {
        if (bytes === 0) return '0 Б';
        
        const k = 1024;
        const sizes = ['Б', 'КБ', 'МБ', 'ГБ'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }
}

// Утилиты для уведомлений
class NotificationManager {
    static showSuccess(message, duration = 5000) {
        this.showNotification(message, 'success', duration);
    }
    
    static showError(message, duration = 8000) {
        this.showNotification(message, 'error', duration);
    }
    
    static showInfo(message, duration = 5000) {
        this.showNotification(message, 'info', duration);
    }
    
    static showNotification(message, type, duration) {
        // Создаем контейнер для уведомлений, если его нет
        let container = document.getElementById('notifications-container');
        if (!container) {
            container = document.createElement('div');
            container.id = 'notifications-container';
            container.style.cssText = `
                position: fixed;
                top: 20px;
                right: 20px;
                z-index: 1100;
                max-width: 400px;
            `;
            document.body.appendChild(container);
        }
        
        // Создаем уведомление
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.style.cssText = `
            background: ${type === 'success' ? '#d4edda' : type === 'error' ? '#f8d7da' : '#d1ecf1'};
            color: ${type === 'success' ? '#155724' : type === 'error' ? '#721c24' : '#0c5460'};
            border: 1px solid ${type === 'success' ? '#c3e6cb' : type === 'error' ? '#f5c6cb' : '#bee5eb'};
            border-radius: 8px;
            padding: 1rem;
            margin-bottom: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            animation: slideIn 0.3s ease-out;
            cursor: pointer;
        `;
        
        notification.textContent = message;
        
        // Добавляем обработчик клика для закрытия
        notification.addEventListener('click', () => {
            this.removeNotification(notification);
        });
        
        container.appendChild(notification);
        
        // Автоматическое удаление
        setTimeout(() => {
            this.removeNotification(notification);
        }, duration);
    }
    
    static removeNotification(notification) {
        if (notification && notification.parentNode) {
            notification.style.animation = 'slideOut 0.3s ease-in';
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.parentNode.removeChild(notification);
                }
            }, 300);
        }
    }
}

// Добавляем CSS для анимаций уведомлений
const notificationStyles = document.createElement('style');
notificationStyles.textContent = `
    @keyframes slideIn {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    
    @keyframes slideOut {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(100%);
            opacity: 0;
        }
    }
`;
document.head.appendChild(notificationStyles);

// Экспортируем для использования в других скriptах
window.EpubCutter = {
    ApiClient,
    FileValidator,
    NotificationManager,
    closeAllModals
};