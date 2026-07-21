console.log("🚀 Эмоциональный фильтр загружен на страницу!");

// Функция для спавна эмодзи
function spawnEmoji(emoji, rect) {
  const emojiEl = document.createElement('div');
  emojiEl.className = 'emo-filter-emoji';
  emojiEl.innerText = emoji;
  
  emojiEl.style.left = `${rect.right + window.scrollX + 5}px`;
  emojiEl.style.top = `${rect.top + window.scrollY - 15}px`;
  
  document.body.appendChild(emojiEl);
  
  setTimeout(() => {
    if (emojiEl.parentNode) {
      emojiEl.parentNode.removeChild(emojiEl);
    }
  }, 4000);
}

// Отправка текстов пачкой через background.js (обход CORS и Mixed Content)
async function analyzeBatch(texts) {
    return new Promise((resolve) => {
        try {
            chrome.runtime.sendMessage(
                { action: "analyzeBatch", texts: texts },
                (response) => {
                    if (chrome.runtime.lastError) {
                        const err = chrome.runtime.lastError.message || chrome.runtime.lastError;
                        console.error("Ошибка при связи с background скриптом:", err);
                        resolve({ error: err });
                        return;
                    }
                    if (!response) {
                        console.error("Пустой ответ от background script.");
                        resolve({ error: "Empty response" });
                        return;
                    }
                    if (!response.success) {
                        console.error("Ошибка от сервера:", response.error);
                        resolve({ error: response.error, status: response.status });
                        return;
                    }
                    resolve({ data: response.data });
                }
            );
        } catch (e) {
            console.error("Исключение при отправке сообщения:", e);
            resolve({ error: e.toString() });
        }
    });
}

// Локальные переменные состояния скрипта (вместо window.*, которые могут сбрасываться)
let scanPausedUntil = 0;
let isScanning = false;

// Запуск сканирования страницы
async function scanPage() {
    if (isScanning) return;
    if (Date.now() < scanPausedUntil) return; // Ждем окончания паузы (Rate Limit)

<<<<<<< HEAD
    if (targetElements.length === 0) {
        console.log("⚠️ Не найдено подходящих текстовых блоков для анализа.");
        return;
    }
    console.log(`🔍 Отправлено на анализ блоков: ${targetElements.length}`);

    // Помечаем как проверенные
    targetElements.forEach(el => el.dataset.emoChecked = "true");

    // Собираем тексты в массив
    const texts = targetElements.map(el => el.innerText.trim());
    
    // Делаем ОДИН пакетный запрос (batch) к API, чтобы экономить жесткие лимиты Google
    const results = await analyzeBatch(texts);
    console.log("📊 Ответ от сервера:", results);

    if (results && Array.isArray(results) && results.length === targetElements.length) {
        targetElements.forEach((el, index) => {
            const result = results[index];
            if (result && result.is_fake) {
                // Текст манипулятивный. Оборачиваем его.
                const wrapper = document.createElement('span');
                // Если доверие очень низкое, то красное, иначе желтое
                wrapper.className = result.trust_score < 30 ? 'emo-filter-aggression' : 'emo-filter-fake';
=======
    isScanning = true;

    try {
        // Выбираем только важные текстовые блоки
        const elements = Array.from(document.querySelectorAll('h1, h2, h3, p'));
        
        // Берем элементы, которые подходят по размеру и находятся на экране
        const targetElements = elements
            .filter(el => {
                const len = el.innerText.trim().length;
                if (len <= 50 || len >= 1500 || el.dataset.emoChecked) return false;
>>>>>>> be15044a33d676e9c6da0ece6eed380ddb36a0f5
                
                // Проверяем, виден ли элемент на экране (плюс запас в 500px сверху и снизу для предзагрузки)
                const rect = el.getBoundingClientRect();
                const isVisible = rect.top < (window.innerHeight || document.documentElement.clientHeight) + 500 && 
                                  rect.bottom > -500;
                                  
                return isVisible && rect.width > 0 && rect.height > 0;
            })
            .slice(0, 15); // Берем максимум 15 видимых элементов (увеличили батч)

        if (targetElements.length === 0) return;

        // Помечаем как "в процессе"
        targetElements.forEach(el => el.dataset.emoChecked = "pending");

        // Собираем тексты в массив
        const texts = targetElements.map(el => el.innerText.trim());
        
        // Делаем ОДИН пакетный запрос (batch) к API
        const response = await analyzeBatch(texts);

        if (response && response.error) {
            // Если уперлись в лимиты API (HTTP 429), ставим на паузу 60 секунд
            if (response.status === 429 || (typeof response.error === 'string' && response.error.includes("quota"))) {
                console.warn("API лимиты превышены. Пауза 60 секунд...");
                scanPausedUntil = Date.now() + 60000;
                // Сбрасываем pending, чтобы проверить потом
                targetElements.forEach(el => delete el.dataset.emoChecked);
            } else {
                // В случае другой ошибки помечаем как error, чтобы не пытаться снова бесконечно
                targetElements.forEach(el => el.dataset.emoChecked = "error");
            }
            return;
        }

        const results = response && response.data;

        if (results && Array.isArray(results) && results.length === targetElements.length) {
            targetElements.forEach((el, index) => {
                el.dataset.emoChecked = "true"; // Успешно проверено
                
                const result = results[index];
                if (result && typeof result === 'object' && result.is_fake) {
                    // Текст манипулятивный. Оборачиваем его.
                    const wrapper = document.createElement('span');
                    // Если доверие очень низкое, то красное, иначе желтое
                    wrapper.className = result.trust_score < 30 ? 'emo-filter-aggression' : 'emo-filter-fake';
                    
                    // Переносим HTML внутрь спана (чтобы сохранить ссылки)
                    wrapper.innerHTML = el.innerHTML;
                    
                    // Создаем тултип
                    const tooltip = document.createElement('div');
                    tooltip.className = 'emo-filter-tooltip';
                    tooltip.innerText = `🤖 ИИ-Анализ:\n${result.explanation}`;
                    
                    wrapper.appendChild(tooltip);
                    
                    // Заменяем оригинальный контент
                    el.innerHTML = '';
                    el.appendChild(wrapper);

                    // Спавним эмодзи
                    setTimeout(() => {
                        const rect = wrapper.getBoundingClientRect();
                        if (rect.width > 0 && rect.height > 0) {
                            const emoji = result.trust_score < 30 ? '🚩' : '🤡';
                            spawnEmoji(emoji, rect);
                        }
                    }, 500);
                }
            });
        } else {
            // Если ответ странный
            targetElements.forEach(el => el.dataset.emoChecked = "error");
        }
    } finally {
        isScanning = false;
    }
}

<<<<<<< HEAD
// Запускаем сканирование
function startScanning() {
    setTimeout(scanPage, 2000); // Первый запуск чуть позже
    setInterval(scanPage, 20000); // Регулярные запуски каждые 20 секунд (чтобы не превышать лимиты Gemini)
}

// Запускаем сразу (расширения обычно грузятся после загрузки DOM)
startScanning();
=======
// Запускаем через секунду после загрузки
window.addEventListener('load', () => {
    setTimeout(scanPage, 1000);
    // Дополнительно сканируем новые видимые элементы каждые 5 секунд, чтобы не убить лимиты
    setInterval(scanPage, 5000);
});
>>>>>>> be15044a33d676e9c6da0ece6eed380ddb36a0f5
