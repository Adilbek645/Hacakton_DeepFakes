import os
import sqlite3
import json
import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()  # Загружаем переменные из файла .env

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv("BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not BOT_TOKEN or not GEMINI_API_KEY:
    print("❌ ОШИБКА: Убедитесь, что заданы переменные окружения BOT_TOKEN и GEMINI_API_KEY в файле .env.")
    exit(1)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Настраиваем Gemini
genai.configure(api_key=GEMINI_API_KEY)

# Используем модель gemini-3.5-flash, настраиваем на возврат JSON
generation_config = {
  "temperature": 0.2,
  "response_mime_type": "application/json",
}
model = genai.GenerativeModel(
    model_name="gemini-2.5-flash",
    generation_config=generation_config,
    system_instruction=(
        "Ты — независимый фактчекер и эксперт по медиаграмотности. "
        "Анализируй текст на кликбейт, эмоциональные триггеры и манипуляции. "
        "ТВОЙ ОТВЕТ ДОЛЖЕН БЫТЬ СТРОГО В ФОРМАТЕ JSON. "
        "Формат ответа: {\"trust_score\": <от 0 до 100>, \"is_fake\": <true/false>, "
        "\"explanation\": \"<Краткое объяснение на русском или казахском, "
        "почему это фейк или правда, макс 2 предложения>\"}"
    )
)

DB_NAME = "hackathon.db"

def save_check_to_db(user_id: int, content: str, is_fake: bool, trust_score: int, explanation: str):
    """Сохраняет результаты проверки в базу данных."""
    conn = None
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO checks (user_id, content, is_fake, trust_score, explanation)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, content, is_fake, trust_score, explanation))
        conn.commit()
    except sqlite3.Error as e:
        logging.error(f"Ошибка базы данных: {e}")
    finally:
        if conn:
            conn.close()

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    """Хэндлер для команды /start"""
    welcome_text = (
        "Привет! 👋 Я — фактчекер проекта «Глаз» (Powered by Gemini).\n\n"
        "Отправьте мне любую сомнительную новость, текст поста или утверждение, "
        "и я проверю его на дезинформацию, кликбейт и манипуляции."
    )
    await message.answer(welcome_text)

@dp.message(F.text)
async def handle_text_message(message: types.Message):
    """Хэндлер для проверки текста пользователя"""
    user_text = message.text
    user_id = message.from_user.id
    
    processing_msg = await message.answer("🔍 Анализирую текст с помощью Gemini... Пожалуйста, подождите.")
    
    try:
        # Вызов Gemini API (используем to_thread, так как библиотека синхронная)
        response = await asyncio.to_thread(model.generate_content, user_text)
        
        # Парсинг ответа
        result_str = response.text
        result_data = json.loads(result_str)
        
        trust_score = result_data.get("trust_score", 0)
        is_fake = result_data.get("is_fake", True)
        explanation = result_data.get("explanation", "Не удалось сформировать объяснение.")
        
        # Сохранение в БД
        save_check_to_db(user_id, user_text, is_fake, trust_score, explanation)
        
        # Формирование ответа
        status_emoji = "🔴 ФЕЙК / МАНИПУЛЯЦИЯ" if is_fake else "🟢 ПРАВДА"
        reply_text = (
            f"**Вердикт:** {status_emoji}\n"
            f"**Уровень доверия:** {trust_score}%\n\n"
            f"💡 **Объяснение:** {explanation}"
        )
        
        await processing_msg.edit_text(reply_text, parse_mode="Markdown")
        
    except Exception as e:
        logging.error(f"Ошибка при обработке запроса Gemini: {e}")
        await processing_msg.edit_text("❌ Произошла ошибка при анализе текста. Пожалуйста, попробуйте позже.")

async def main():
    print("\n" + "="*60)
    print("🤖 Telegram-бот 'Глаз' (Gemini Edition) успешно запущен!")
    print("💡 Убедитесь, что Flask сервер (app.py) также запущен для дашборда.")
    print("="*60 + "\n")
    
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
