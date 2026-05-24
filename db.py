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


#отправляет в бд все заполненные юзером данные, использовать на кнопку отправить на модерацию или чет такое
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


#выдает список всех сущ-их авторов задач
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


#выдает список сущ-их тэгов
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


#выдает список сущ-их языков
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


#отдаст список словарей с id и всем остальным мета задач которые ожидают одобрения админов
def sptasks_na_odobrenie():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT id, title, authors, tags, olympiad, year, language FROM tasks WHERE status = 'pending'")
    na_ids = cursor.fetchall()
    sp_ids = []
    for sl in na_ids:
        sp_ids.append(dict(sl))
    conn.close
    return sp_ids


#одобрение задачи (по id)
def odobrenie(task_id):
    conn = sqlite3.connect(DB)
    cursor = conn.cursor()
    cursor.execute("SELECT sender_id FROM tasks WHERE id = ?", (task_id,))
    sender = cursor.fetchone()
    cursor.execute("UPDATE tasks SET status = 'approved' WHERE id = ?", (task_id,))
    conn.commit()
    conn.close()
    if sender:
        return sender[0]
    else:
        return None


#удаление задачи (по id)
def udalenie(task_id):
    conn = sqlite3.connect(DB)
    cursor = conn.cursor()
    cursor.execute("SELECT sender_id FROM tasks WHERE id = ?", (task_id,))
    sender = cursor.fetchone()
    cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    conn.commit()
    conn.close()
    if sender:
        return sender[0]
    else:
        return None


#отдаст в виде словаря строку со всеми данными задачи по ее id
def vivod_na_check(task_id):
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
    sl = cursor.fetchone()
    conn.close
    if sl:
        return dict(sl)
    else:
        return None


#отдаст в виде списка словарей все данные задач (1 и больше) по одному названию
def task_po_title(tasks_title):
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tasks WHERE title = ?", (tasks_title,))
    all_tasks_title = cursor.fetchall()
    sp_tasks_title = []
    for sl in all_tasks_title:
        sp_tasks_title.append(dict(sl))
    conn.close
    return sp_tasks_title


#вытаскивает в виде списка словарей все задачи одной олимпиады
def task_po_olimp(tasks_olimp):
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tasks WHERE olympiad = ?", (tasks_olimp,))
    all_tasks_olimp = cursor.fetchall()
    sp_tasks_olimp = []
    for sl in all_tasks_olimp:
        sp_tasks_olimp.append(dict(sl))
    conn.close
    return sp_tasks_olimp


#вытакивает в виде списка словарей все задачи одного года
def task_po_year(tasks_year):
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tasks WHERE year = ?", (tasks_year,))
    all_tasks_year = cursor.fetchall()
    sp_tasks_year = []
    for sl in all_tasks_year:
        sp_tasks_year.append(dict(sl))
    conn.close
    return sp_tasks_year

#поиск в который на вход пожалуйста сделайте списки во всех переменных
def top_search(ztitle = None, zauthors = None, ztags = None, zolymp = None, zyear = None, zlang = None):
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tasks WHERE status = 'approved'")
    all_t = cursor.fetchall()
    conn.close()
    sp_matches = []
    for task in all_t:
        matches = 0
        if (ztitle and task['title']):
            for tit in ztitle:
                if tit == task['title']:
                    matches += 1
                    break
        if (zolymp and task['olympiad']):
            for ol in zolymp:
                if ol == task['olympiad']:
                    matches += 1
                    break
        if (zyear and task['year']):
            for ye in zyear:
                if str(ye) == str(task['year']):
                    matches += 1
                    break
        if (zauthors and task['authors']):
            sp_authors = []
            for sl in task['authors'].split(','):
                sp_authors.append(sl.strip())
            for au in zauthors:
                if str(au) in sp_authors:
                    matches += 1
        if (ztags and task['tags']):
            sp_tags = []
            for sl in task['tags'].split(','):
                sp_tags.append(sl.strip())
            for tag in ztags:
                if tag in sp_tags:
                    matches += 1
        if (zlang and task['language']):
            sp_langs = []
            for sl in task['language'].split(','):
                sp_langs.append(sl.strip())
            for lan in zlang:
                if lan in sp_langs:
                    matches += 1
        if matches >= 1:
            di_task = dict(task)
            di_task['matches'] = matches
            sp_matches.append(di_task)

    sp_matches.sort(key=lambda x: x['matches'], reverse=True)
    return sp_matches[:5]


#редактирует любую ячейку задачи по ее id и указанию столбца для редактирования
def redaktor(task_id, stolb, new):
    real_stolbs = ['task_text', 'answer_text', 'title', 'authors', 'tags', 'olympiad', 'year', 'language']
    if stolb in real_stolbs:
        conn = sqlite3.connect(DB)
        cursor = conn.cursor()
        cursor.execute(f"UPDATE tasks SET {stolb} = ? WHERE id = ?", (new, task_id))
        conn.commit()
        conn.close
    else:
        print(f'Нет столбца с именем {stolb}')


#хз надо или нет но эта функци выводит просто список словарей с данными всех вообще задач (и одобренных и нет)
def dai_all():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tasks")
    all_tasks = cursor.fetchall()
    sp_all_tasks = []
    for sl in all_tasks:
        sp_all_tasks.append(dict(sl))
    conn.close()
    return sp_all_tasks


#выдает список названий задач без повторов, учитывает пробелы (берет название за строку)
def dai_titles():
    conn = sqlite3.connect(DB)
    cursor = conn.cursor()
    cursor.execute("SELECT title FROM tasks WHERE title IS NOT NULL AND status = 'approved'")
    all_titles = cursor.fetchall()
    conn.close()
    set_titles = set()
    for ti in all_titles:
        clean_ti = ti[0].strip()
        if clean_ti:
            set_titles.add(clean_ti)
    return list(set_titles)

#выдает список названий олимпиад без повторов, учитывает пробелы
def dai_olympiads():
    conn = sqlite3.connect(DB)
    cursor = conn.cursor()
    cursor.execute("SELECT olympiad FROM tasks WHERE olympiad IS NOT NULL AND status = 'approved'")
    all_olymp = cursor.fetchall()
    conn.close()
    set_olymp = set()
    for ol in all_olymp:
        clean_ol = ol[0].strip()
        if clean_ol:
            set_olymp.add(clean_ol)
    return list(set_olymp)

#выдает список лет
def dai_years():
    conn = sqlite3.connect(DB)
    cursor = conn.cursor()
    cursor.execute("SELECT year FROM tasks WHERE year IS NOT NULL AND status = 'approved'")
    all_years = cursor.fetchall()
    conn.close()

    set_years = set()
    for ye in all_years:
        if ye[0] is not None:
            set_years.add(ye[0])
    return list(set_years)


#выдает список задач на один язык
def task_po_lang(lang):
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('''
                   SELECT id, title, language FROM tasks WHERE language LIKE ? AND status = "approved"
                   ''', (f"%{lang}%",))
    all_tasks = cursor.fetchall()
    sp_tasks = []
    for sl in all_tasks:
        sp_tasks.append(dict(sl))
    conn.close()
    return sp_tasks


#выдает список задач с определенным тегом
def task_po_tag(tag):
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, title, language FROM tasks WHERE tags LIKE ? AND status = "approved"
        ''', (f"%{tag}%",)
    )
    all_tasks = cursor.fetchall()
    sp_tasks = []
    for sl in all_tasks:
        sp_tasks.append(dict(sl))
    conn.close()
    return sp_tasks


#выдает список задач с одним автором
def task_po_author(author):
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, title, language FROM tasks WHERE authors LIKE ? AND status = "approved"
                   ''', (f"%{author}%",)
    )
    all_tasks = cursor.fetchall()
    sp_tasks = []
    for sl in all_tasks:
        sp_tasks.append(dict(sl))
    conn.close()
    return sp_tasks


def task_po_id(tasks_id):
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT task_text, task_file_id, answer_text, answer_file_id FROM tasks WHERE id = ?", (tasks_id,))
    task = cursor.fetchone()
    conn.close
    if task:
        if task['task_text']:
            my_task_text = task['task_text']
        else:
            my_task_text = task['task_file_id']
        if ['answer_text']:
            my_task_answer = task['answer_text']
        else:
            my_task_answer = task['answer_file_id']
        return my_task_text, my_task_answer
    else:
        return None


def change_status(task_id):
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("UPDATE tasks SET status = 'pending' WHERE id = ?", (task_id,))
    conn.commit()
    conn.close