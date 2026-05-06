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


def dai_authors():
    conn = sqlite3.connect(DB)
    cursor = conn.cursor()
    cursor.execute("SELECT authors FROM tasks WHERE authors IS NOT NULL AND status = 'approved'")
    all_authors = cursor.fetchall()
    conn.close()
    set_authors = set()
    for au in all_authors:
        au_s = au[0]
        au_s = au_s.split(',')
        for sl in au_s:
            clean_sl = sl.strip()
            if clean_sl:
                set_authors.add(clean_sl)
    return list(set_authors)


def dai_tags():
    conn = sqlite3.connect(DB)
    cursor = conn.cursor()
    cursor.execute("SELECT tags FROM tasks WHERE tags IS NOT NULL AND status ='approved'")
    all_tags = cursor.fetchall()
    conn.close
    set_tags = set()
    for ta in all_tags:
        ta_s = ta[0]
        ta_s = ta_s.split(',')
        for sl in ta_s:
            clean_sl = sl.strip().lower()
            if clean_sl:
                set_tags.add(clean_sl)
    return list(set_tags)


def dai_lang():
    conn = sqlite3.connect(DB)
    cursor = conn.cursor()
    cursor.execute("SELECT language FROM tasks WHERE language IS NOT NULL AND status ='approved'")
    all_lang = cursor.fetchall()
    conn.close
    set_lang = set()
    for la in all_lang:
        la_s = la[0]
        la_s = la_s.split(',')
        for sl in la_s:
            clean_sl = sl.strip().lower()
            if clean_sl:
                set_lang.add(clean_sl)
    return list(set_lang)


def sptasks_na_odobrenie():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT id, language FROM tasks WHERE status = 'pending'")
    na_ids = cursor.fetchall()
    sp_ids = []
    for sl in na_ids:
        sp_ids.append(dict(sl))
    conn.close
    return sp_ids


def vivod_na_check(task_id):
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM task WHERE id = ?", (task_id))
    sl = cursor.fetchone()
    conn.close
    if sl:
        return dict(sl)
    else: 
        return None