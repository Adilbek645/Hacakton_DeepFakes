import sqlite3
from flask import Flask, render_template, send_file
import os
import io
from PIL import Image

app = Flask(__name__)
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

if __name__ == '__main__':
    # Включаем debug=True для удобства разработки
    app.run(debug=True, host='0.0.0.0', port=5000)
