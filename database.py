import sqlite3
import os

DB_NAME = "hackathon.db"

def init_db():
    """
    Инициализирует базу данных SQLite и создает таблицу checks, если она не существует.
    """
    conn = None
    try:
        # Подключаемся к базе данных
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        # Создаем таблицу checks
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS checks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                content TEXT,
                is_fake BOOLEAN,
                trust_score INTEGER,
                explanation TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Сохраняем изменения
        conn.commit()
        print(f"База данных {DB_NAME} успешно инициализирована. Таблица 'checks' готова.")
    except sqlite3.Error as e:
        print(f"Ошибка при работе с базой данных SQLite: {e}")
    finally:
        # Всегда закрываем соединение
        if conn:
            conn.close()

if __name__ == "__main__":
    init_db()
    print("Запуск database.py завершен. База данных готова.")
