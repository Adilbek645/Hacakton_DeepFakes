import os
import sqlite3
import json
import asyncio
import logging
import aiohttp
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()  # Загружаем переменные из файла .env

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv("BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
SIGHTENGINE_API_USER = os.getenv("SIGHTENGINE_API_USER")
SIGHTENGINE_API_SECRET = os.getenv("SIGHTENGINE_API_SECRET")

if not BOT_TOKEN or not GEMINI_API_KEY or not SIGHTENGINE_API_USER or not SIGHTENGINE_API_SECRET:
    print("❌ ОШИБКА: Убедитесь, что заданы переменные окружения BOT_TOKEN, GEMINI_API_KEY, SIGHTENGINE_API_USER и SIGHTENGINE_API_SECRET в файле .env.")
    exit(1)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Настраиваем Gemini
genai.configure(api_key=GEMINI_API_KEY)

# Используем модель gemini-2.5-flash, настраиваем на возврат JSON
generation_config = {
  "temperature": 0.2,
  "response_mime_type": "application/json",
}
model = genai.GenerativeModel(
    model_name="gemini-2.5-flash",
    generation_config=generation_config,
    system_instruction=(
        "Ты — независимый фактчекер и эксперт по медиаграмотности. "
        "Анализируй предоставленный контент на признаки дезинформации, генерации нейросетью, дипфейка, кликбейта и манипуляций. "
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
        "Привет! 👋 Я — фактчекер проекта «Глаз».\n\n"
        "Отправьте мне любую сомнительную новость (текст), и я проверю её на дезинформацию через Gemini.\n"
        "Или отправьте мне фотографию, и я проверю её на дипфейк с помощью Sightengine AI!"
    )
    await message.answer(welcome_text)

@dp.message(F.text)
async def handle_text_message(message: types.Message):
    """Хэндлер для проверки текста пользователя"""
    user_text = message.text
    user_id = message.from_user.id
    
    processing_msg = await message.answer("🔍 Анализирую текст с помощью Gemini... Пожалуйста, подождите.")
    
    try:
        # Вызов Gemini API
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
        if trust_score >= 80:
            status_emoji = "🟢 ПРАВДА"
        elif trust_score >= 50:
            status_emoji = "🟡 ВЕРОЯТНО ПРАВДА / НЕОДНОЗНАЧНО"
        elif trust_score >= 20:
            status_emoji = "🟠 МАНИПУЛЯЦИЯ / ПОЛУПРАВДА"
        else:
            status_emoji = "🔴 ФЕЙК"
            
        reply_text = (
            f"**Вердикт:** {status_emoji}\n"
            f"**Уровень доверия:** {trust_score}%\n\n"
            f"💡 **Объяснение:** {explanation}"
        )
        
        await processing_msg.edit_text(reply_text, parse_mode="Markdown")
        
    except Exception as e:
        logging.error(f"Ошибка при обработке запроса Gemini: {e}")
        await processing_msg.edit_text("❌ Произошла ошибка при анализе текста. Возможно, вы превысили лимит (429). Подождите 1 минуту.")

@dp.message(F.photo)
async def handle_photo_message(message: types.Message):
    """Хэндлер для проверки фотографий пользователя через Sightengine API"""
    user_id = message.from_user.id
    
    processing_msg = await message.answer("🖼️ Сканирую изображение через нейросеть Sightengine... Пожалуйста, подождите.")
    
    try:
        # Получаем фото в лучшем качестве
        photo = message.photo[-1]
        file_info = await bot.get_file(photo.file_id)
        downloaded_file = await bot.download_file(file_info.file_path)
        image_bytes = downloaded_file.read()
        
        # Сохранение на диск
        import time
        os.makedirs(os.path.join("static", "uploads"), exist_ok=True)
        filename = f"{user_id}_{int(time.time())}.jpg"
        filepath = os.path.join("static", "uploads", filename)
        with open(filepath, "wb") as f:
            f.write(image_bytes)
        
        # Подготовка данных для Sightengine
        data = aiohttp.FormData()
        data.add_field('models', 'genai,deepfake')
        data.add_field('api_user', SIGHTENGINE_API_USER)
        data.add_field('api_secret', SIGHTENGINE_API_SECRET)
        data.add_field('media', image_bytes, filename='image.jpg', content_type='image/jpeg')
        
        # Вызов Sightengine API
        async with aiohttp.ClientSession() as session:
            async with session.post('https://api.sightengine.com/1.0/check.json', data=data) as resp:
                result_data = await resp.json()
                
                if result_data.get("status") != "success":
                    error_msg = result_data.get("error", {}).get("message", "Unknown API error")
                    raise Exception(f"Sightengine API Error: {error_msg}")
        
        # Парсинг ответа
        # Sightengine возвращает вероятности (от 0.0 до 1.0)
        ai_prob = result_data.get("type", {}).get("ai_generated", 0.0)
        deepfake_prob = result_data.get("type", {}).get("deepfake", 0.0)
        
        ai_percent = int(ai_prob * 100)
        deepfake_percent = int(deepfake_prob * 100)
        
        max_prob = max(ai_prob, deepfake_prob)
        
        # Конвертация в наш trust_score (1.0 = 0% доверия, 0.0 = 100% доверия)
        trust_score = int((1.0 - max_prob) * 100)
        is_fake = trust_score < 50
        
        # Формирование ответа
        if trust_score >= 80:
            status_emoji = "🟢 ПРАВДА (Оригинал)"
            explanation = "Нейросети уверены, что это подлинная фотография, без следов генерации ИИ или подмены лица."
        elif trust_score >= 50:
            status_emoji = "🟡 ВЕРОЯТНО ОРИГИНАЛ / НЕОДНОЗНАЧНО"
            explanation = "Модели склоняются к тому, что фото настоящее, но есть небольшая вероятность искажений или легкой обработки."
        elif trust_score >= 20:
            status_emoji = "🟠 ПОДОЗРЕНИЕ НА МАНИПУЛЯЦИЮ"
            if ai_prob > deepfake_prob:
                explanation = "Обнаружены серьезные признаки ИИ-генерации (Midjourney, DALL-E и т.д.)."
            else:
                explanation = "Обнаружены серьезные признаки дипфейка или фотомонтажа лица."
        else:
            status_emoji = "🔴 ФЕЙК / МАНИПУЛЯЦИЯ"
            if ai_prob > deepfake_prob:
                explanation = "С высокой вероятностью это полностью сгенерированное ИИ изображение."
            else:
                explanation = "С высокой вероятностью это глубокий дипфейк (подмена лица)."
            
        # Сохранение в БД
        save_check_to_db(user_id, f"IMAGE:{filename}", is_fake, trust_score, explanation)
            
        reply_text = (
            f"**Вердикт по фото:** {status_emoji}\n"
            f"**Уровень доверия:** {trust_score}%\n\n"
            f"🤖 **ИИ-генерация:** {ai_percent}% вероятность\n"
            f"🎭 **Дипфейк (лица):** {deepfake_percent}% вероятность\n\n"
            f"💡 **Анализ:** {explanation}"
        )
        
        await processing_msg.edit_text(reply_text, parse_mode="Markdown")
        
    except Exception as e:
        logging.error(f"Ошибка при обработке фото Sightengine: {e}")
        await processing_msg.edit_text("❌ Произошла ошибка при анализе фотографии. Пожалуйста, проверьте ключи доступа или попробуйте позже.")

@dp.message(F.video)
async def handle_video_message(message: types.Message):
    """Хэндлер для проверки видео пользователя через Sightengine API"""
    user_id = message.from_user.id
    
    if message.video.file_size > 20 * 1024 * 1024:
        await message.answer("❌ Размер видео превышает 20 МБ. Бот не может скачивать файлы такого размера из-за ограничений Telegram.")
        return
        
    processing_msg = await message.answer("🎥 Сканирую видео кадр за кадром через нейросеть Sightengine... Пожалуйста, подождите. Это может занять до минуты.")
    
    try:
        # Получаем видео
        file_info = await bot.get_file(message.video.file_id)
        downloaded_file = await bot.download_file(file_info.file_path)
        video_bytes = downloaded_file.read()
        
        # Сохранение на диск
        import time
        os.makedirs(os.path.join("static", "uploads"), exist_ok=True)
        filename = f"{user_id}_{int(time.time())}.mp4"
        filepath = os.path.join("static", "uploads", filename)
        with open(filepath, "wb") as f:
            f.write(video_bytes)
        
        # Подготовка данных для Sightengine (Синхронный API для видео)
        data = aiohttp.FormData()
        data.add_field('models', 'genai,deepfake')
        data.add_field('api_user', SIGHTENGINE_API_USER)
        data.add_field('api_secret', SIGHTENGINE_API_SECRET)
        data.add_field('media', video_bytes, filename='video.mp4', content_type='video/mp4')
        
        # Вызов Sightengine API
        async with aiohttp.ClientSession() as session:
            async with session.post('https://api.sightengine.com/1.0/video/check-sync.json', data=data) as resp:
                result_data = await resp.json()
                
                if result_data.get("status") != "success":
                    error_msg = result_data.get("error", {}).get("message", "Unknown API error")
                    raise Exception(f"Sightengine API Error: {error_msg}")
        
        # Парсинг ответа (Sightengine возвращает массив frames для видео)
        frames = result_data.get("data", {}).get("frames", [])
        
        max_ai_prob = 0.0
        max_deepfake_prob = 0.0
        
        for frame in frames:
            frame_ai = frame.get("type", {}).get("ai_generated", 0.0)
            frame_df = frame.get("type", {}).get("deepfake", 0.0)
            max_ai_prob = max(max_ai_prob, frame_ai)
            max_deepfake_prob = max(max_deepfake_prob, frame_df)
        
        ai_percent = int(max_ai_prob * 100)
        deepfake_percent = int(max_deepfake_prob * 100)
        
        max_prob = max(max_ai_prob, max_deepfake_prob)
        
        # Конвертация в наш trust_score
        trust_score = int((1.0 - max_prob) * 100)
        is_fake = trust_score < 50
        
        # Формирование ответа
        if trust_score >= 80:
            status_emoji = "🟢 ПРАВДА (Оригинал)"
            explanation = "Нейросети уверены, что это подлинное видео, без следов генерации ИИ или подмены лица."
        elif trust_score >= 50:
            status_emoji = "🟡 ВЕРОЯТНО ОРИГИНАЛ / НЕОДНОЗНАЧНО"
            explanation = "Модели склоняются к тому, что видео настоящее, но есть подозрительные кадры."
        elif trust_score >= 20:
            status_emoji = "🟠 ПОДОЗРЕНИЕ НА МАНИПУЛЯЦИЮ"
            if max_ai_prob > max_deepfake_prob:
                explanation = "В видео обнаружены кадры с серьезными признаками ИИ-генерации."
            else:
                explanation = "В видео обнаружены кадры с серьезными признаками дипфейка или фотомонтажа лица."
        else:
            status_emoji = "🔴 ФЕЙК / МАНИПУЛЯЦИЯ"
            if max_ai_prob > max_deepfake_prob:
                explanation = "С высокой вероятностью это полностью сгенерированное ИИ видео."
            else:
                explanation = "С высокой вероятностью это глубокий дипфейк (видео с подменой лица)."
            
        # Сохранение в БД
        save_check_to_db(user_id, f"VIDEO:{filename}", is_fake, trust_score, explanation)
            
        reply_text = (
            f"**Вердикт по видео:** {status_emoji}\n"
            f"**Уровень доверия:** {trust_score}%\n\n"
            f"🤖 **ИИ-генерация:** {ai_percent}% вероятность на худшем кадре\n"
            f"🎭 **Дипфейк (лица):** {deepfake_percent}% вероятность на худшем кадре\n\n"
            f"💡 **Анализ:** {explanation}"
        )
        
        await processing_msg.edit_text(reply_text, parse_mode="Markdown")
        
    except Exception as e:
        logging.error(f"Ошибка при обработке видео Sightengine: {e}")
        await processing_msg.edit_text("❌ Произошла ошибка при анализе видео. Возможно, сервер перегружен.")

async def main():
    print("\n" + "="*60)
    print("🤖 Telegram-бот 'Глаз' успешно запущен!")
    print("🧠 Используемые API: Gemini 2.5 (Текст) + Sightengine (Фото)")
    print("💡 Убедитесь, что Flask сервер (app.py) также запущен для дашборда.")
    print("="*60 + "\n")
    
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
