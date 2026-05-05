import sqlite3


DB = 'olympiad_tasks.db'
def init_db():
    conn = sqlite3.connect(DB)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            -- здесь лежит Telegram ID приславшего
            sender_id INTEGER NOT NULL,

            -- Условие задачи
            task_text TEXT,
            task_file_id TEXT,

            -- Ответы
            answer_text TEXT,
            answer_file_id TEXT,

            -- Метаданные
            title TEXT,
            authors TEXT,
            tags TEXT,
            olympiad TEXT,
            year INTEGER,
            language TEXT,

            -- Технические поля
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()


def add_task(sender_id, title=None, task_text=None, task_file_id=None,
             answer_text=None, answer_file_id=None, authors=None,
             tags=None, olympiad=None, year=None, language=None):
    conn = sqlite3.connect(DB)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO tasks (
            sender_id, title, task_text, task_file_id,
            answer_text, answer_file_id,
            authors, tags, olympiad, year, language
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (sender_id, title, task_text, task_file_id, answer_text, answer_file_id, authors, tags, olympiad, year, language))
    conn.commit()
    conn.close()