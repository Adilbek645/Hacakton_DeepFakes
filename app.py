import sqlite3
from flask import Flask, render_template, send_file, request, jsonify
from flask_cors import CORS
import os
import io
import json
from PIL import Image
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()

app = Flask(__name__)
CORS(app) # Разрешаем запросы из расширения Chrome

# Настраиваем Gemini
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    
    generation_config = {
      "temperature": 0.2,
      "response_mime_type": "application/json",
    }
    
    # Отключаем встроенные фильтры безопасности, иначе он будет блокировать агрессивные новости
    safety_settings = [
        {
            "category": "HARM_CATEGORY_HARASSMENT",
            "threshold": "BLOCK_NONE"
        },
        {
            "category": "HARM_CATEGORY_HATE_SPEECH",
            "threshold": "BLOCK_NONE"
        },
        {
            "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
            "threshold": "BLOCK_NONE"
        },
        {
            "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
            "threshold": "BLOCK_NONE"
        }
    ]

    model = genai.GenerativeModel(
        model_name="gemini-flash-latest",
        generation_config=generation_config,
        safety_settings=safety_settings,
        system_instruction=(
            "Ты — детектор манипуляций и дезинформации. Проанализируй текст на признаки кликбейта, "
            "манипулятивного языка, агрессии, теорий заговора и эмоционального давления. "
            "Отвечай СТРОГО в формате JSON: {\"is_fake\": <true/false>, \"trust_score\": <0-100 (100=полностью безопасно)>, "
            "\"explanation\": \"Краткое объяснение (1-2 предложения), в чем заключается манипуляция или почему текст нормальный.\"}"
        )
    )
else:
    model = None

DB_NAME = "hackathon.db"

def get_latest_checks():
    """
    Извлекает последние 15 записей из таблицы checks.
    """
    conn = None
    try:
        conn = sqlite3.connect(DB_NAME)
        # row_factory = sqlite3.Row позволяет обращаться к колонкам по именам, как в словаре
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, user_id, content, is_fake, trust_score, explanation, timestamp 
            FROM checks 
            ORDER BY timestamp DESC 
            LIMIT 15
        ''')
        rows = cursor.fetchall()
        return rows
    except sqlite3.Error as e:
        print(f"Ошибка при чтении из базы данных SQLite: {e}")
        return []
    finally:
        # Обязательно закрываем соединение после выполнения запроса
        if conn:
            conn.close()

@app.route('/')
def dashboard():
    checks = get_latest_checks()
    return render_template('index.html', checks=checks)

@app.route('/image/<filename>')
def serve_image(filename):
    filepath = os.path.join("static", "uploads", filename)
    if not os.path.exists(filepath):
        return "Image not found", 404
    
    try:
        # Открываем изображение через Pillow
        img = Image.open(filepath)
        
        # Конвертируем в RGB если нужно (чтобы избежать проблем при сохранении JPEG)
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
            
        # Создаем миниатюру для оптимизации загрузки дашборда
        img.thumbnail((400, 400))
        
        # Сохраняем во временный буфер в оперативной памяти
        img_io = io.BytesIO()
        img.save(img_io, 'JPEG', quality=85)
        img_io.seek(0)
        
        return send_file(img_io, mimetype='image/jpeg')
    except Exception as e:
        print(f"Error processing image with PIL: {e}")
        return "Error processing image", 500

@app.route('/api/analyze', methods=['POST', 'OPTIONS'])
def analyze_text():
    # Обработка preflight-запроса от браузера
    if request.method == 'OPTIONS':
        return '', 200
        
    if not model:
        return jsonify({"error": "Gemini API key not configured"}), 500
        
    data = request.json
    text = data.get('text', '')
    
    if not text:
        return jsonify({"error": "No text provided"}), 400
        
    try:
        response = model.generate_content(text)
        result = json.loads(response.text)
        return jsonify(result)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/api/analyze_batch', methods=['POST', 'OPTIONS'])
def analyze_batch():
    if request.method == 'OPTIONS':
        return '', 200
        
    if not model:
        return jsonify({"error": "Gemini API key not configured"}), 500
        
    data = request.json
    texts = data.get('texts', [])
    
    if not texts:
        return jsonify({"error": "No texts provided"}), 400
        
    try:
        prompt = (
            "У меня есть список текстов. Оцени каждый текст на признаки кликбейта, манипулятивного языка, агрессии, теорий заговора и эмоционального давления.\n\nТексты:\n"
        )
        for i, text in enumerate(texts):
            prompt += f"[{i}]: {text}\n\n"
            
        prompt += "Отвечай СТРОГО в формате JSON массива (list of objects), где каждый объект имеет ключи: is_fake (boolean), trust_score (integer 0-100, 100=полностью безопасно) и explanation (краткая строка). Порядок элементов в массиве должен СТРОГО соответствовать переданному списку текстов."
        
        response = model.generate_content(prompt)
        result = json.loads(response.text)
        return jsonify(result)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # Включаем debug=True для удобства разработки
    app.run(debug=True, host='0.0.0.0', port=5000)
