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
        chrome.runtime.sendMessage(
            { action: "analyzeBatch", texts: texts },
            (response) => {
                if (chrome.runtime.lastError || !response || !response.success) {
                    console.error("Ошибка при связи с сервером через background:", chrome.runtime.lastError || (response && response.error));
                    resolve(null);
                } else {
                    resolve(response.data);
                }
            }
        );
    });
}

// Запуск сканирования страницы
async function scanPage() {
    // Выбираем только важные текстовые блоки, чтобы не превысить лимит API
    const elements = Array.from(document.querySelectorAll('h1, h2, h3, p'));
    
    // Берем элементы (абзацы и заголовки), в которых от 50 до 1500 символов
    const targetElements = elements
        .filter(el => {
            const len = el.innerText.trim().length;
            // Пропускаем уже проверенные
            return len > 50 && len < 1500 && !el.dataset.emoChecked;
        })
        .slice(0, 10);

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
    }
}

// Запускаем сканирование
function startScanning() {
    setTimeout(scanPage, 2000); // Первый запуск чуть позже
    setInterval(scanPage, 20000); // Регулярные запуски каждые 20 секунд (чтобы не превышать лимиты Gemini)
}

// Запускаем сразу (расширения обычно грузятся после загрузки DOM)
startScanning();
