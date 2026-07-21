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

// Отправка текстов пачкой через background.js
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
    const elements = Array.from(document.querySelectorAll('h1, h2, h3, p'));
    
    const targetElements = elements
        .filter(el => {
            const len = el.innerText.trim().length;
            return len > 50 && len < 1500 && !el.dataset.emoChecked;
        })
        .slice(0, 10);

    if (targetElements.length === 0) {
        return;
    }
    console.log(`🔍 Отправлено на анализ блоков: ${targetElements.length}`);

    targetElements.forEach(el => el.dataset.emoChecked = "true");

    const texts = targetElements.map(el => el.innerText.trim());
    
    const results = await analyzeBatch(texts);
    if (!results) {
        console.warn("⚠️ Ошибка получения данных. Возможно лимит запросов.");
        // Снимаем пометку, чтобы можно было проверить потом
        targetElements.forEach(el => delete el.dataset.emoChecked);
        return;
    }
    
    console.log("📊 Ответ от сервера:", results);

    if (results && Array.isArray(results) && results.length === targetElements.length) {
        targetElements.forEach((el, index) => {
            const result = results[index];
            if (result && result.is_fake) {
                const wrapper = document.createElement('span');
                wrapper.className = result.trust_score < 30 ? 'emo-filter-aggression' : 'emo-filter-fake';
                wrapper.innerHTML = el.innerHTML;
                
                const tooltip = document.createElement('div');
                tooltip.className = 'emo-filter-tooltip';
                tooltip.innerText = `🤖 ИИ-Анализ:\n${result.explanation}`;
                wrapper.appendChild(tooltip);
                
                el.innerHTML = '';
                el.appendChild(wrapper);

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
    setInterval(scanPage, 20000); // Каждые 20 секунд
}

startScanning();
