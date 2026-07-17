import sqlite3
from flask import Flask, render_template
import os

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
def index():
    """
    Главная страница (дашборд).
    Извлекает данные из БД и рендерит HTML-шаблон.
    """
    checks = get_latest_checks()
    return render_template('index.html', checks=checks)

if __name__ == '__main__':
    print("\n" + "="*60)
    print("🚀 Flask сервер 'Көз' запущен!")
    print("👉 Откройте http://127.0.0.1:5000 в браузере для просмотра дашборда.")
    print("💡 ВАЖНО: Запустите bot.py в ДРУГОМ терминале для приема сообщений.")
    print("="*60 + "\n")
    
    app.run(debug=True)
