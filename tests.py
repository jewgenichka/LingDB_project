import db


# тесты
if __name__ == "__main__":
    db.init_db()
    komanda = input("Введите команду: ")
    if komanda == "add":
        print("ТЕСТИРОВАНИЕ ДОБАВЛЕНИЯ ЗАДАЧИ")
        ttext = input("Введите текст задачи: ")
        tanswer = input("Введите текст ответа на задачу: ")
        ttitle = input("Введите заголовок задачи: ")
        tauthors = input("Введите имя автора: ")
        ttags = input("Введите теги через запятую: ")
        tolympiad = input("Введите олимпиаду задачи: ")
        if tolympiad:
            tyear = input("Введите год олимпиады: ")
        else:
            tyear = None
        tlanguage = input("На какой язык составлена задача: ")
        tsender_id = 1234567
        tfile_id = "file_id_test_123"
        tanswer_file_id = "answer_test_123"
        print("\nПробую сохранить в базу...")
        try:
            db.add_task(
                tsender_id,
                ttitle,
                ttext,
                tfile_id,
                tanswer,
                tanswer_file_id,
                tauthors,
                ttags,
                tolympiad,
                tyear,
                tlanguage)
            print("УСПЕШНО! Задача сохранена.")
        except Exception as e:
            print(f"ОШИБКА при сохранении: {e}")
        print("\nПРОВЕРКА СПИСКА НА ОДОБРЕНИЕ")
        pending_tasks = db.sptasks_na_odobrenie()
        if pending_tasks:
            print(f"Сейчас на проверке задач: {len(pending_tasks)}")
            for t in pending_tasks:
                print(f"[{t['id']}] {t['language']}")
        else:
            print("В базе пусто. ЧТО-ТО НЕ ТАК.")
    if komanda == "del":
        print("ТЕСТИРОВАНИЕ УДАЛЕНИЯ ЗАДАЧИ")
        a = input("Введите id задачи, которую хотите удалить: ")
        try:
            db.udalenie(a)
            print("УСПЕШНО! ВЫ УНИЧТОЖИИЛИ ЭТУ ЗАДАЧУ")
        except Exception as e:
            print(f"ОШИБКА при удалении: {e}")
    if komanda == "dobro":
        print("ТЕСТИРОВАНИЕ ОДОБРЕНИЯ ЗАДАЧИ")
        a = input("Введите id задачи, которую хотите одобрить: ")
        try:
            db.odobrenie(a)
            print("УСПЕШНО! ВЫ ОДОБРИЛИ ЭТУ ЗАДАЧУ")
        except Exception as e:
            print(f"ОШИБКА при одобрение: {e}")
    if komanda == 'all':
        all_ta = db.dai_all()
        for t in all_ta:
            print(f"[{t['id']}] {t['title']} {t['language']}")
    if komanda == 'dai_au':
        print(db.dai_authors())
    if komanda == 'dai_tags':
        print(db.dai_tags())
    if komanda == 'dai_lang':
        print(db.dai_lang())
    if komanda == 'check_task':
        id_tas = input('Введите id задачи, которую хотите увидеть: ')
        print(db.vivod_na_check(id_tas))
    if komanda == 'tpo_olimp':
        t_olimp = input('Введите олимпиаду: ')
        sp_po_olimp = db.task_po_olimp(t_olimp)
        for t in sp_po_olimp:
            print(f"[{t['id']}] {t['title']} {t['language']}")
    if komanda == 'red':
        id_z = input('Какую задачу хотите изменить? ')
        stolb1 = input('Какой столбец: ')
        new_val = input('Введите новое значение: ')
        try:
            db.redaktor(id_z, stolb1, new_val)
            print('Вы успешно отредактировали задачу!')
        except Exception as e:
            print(f'ОШИБКА при редактировании: {e}')
    if komanda == 'tpo_year':
        t_year = input('Введите год: ')
        sp_po_year = db.task_po_year(t_year)
        for t in sp_po_year:
            print(f"[{t['id']}] {t['title']} {t['language']}")
    if komanda == 'search':
        ttitle = list(input("Введите заголовок задачи: "))
        tauthors = input("Введите имя авторов: ").strip().split(', ')
        ttags = input("Введите тэги через запятую: ").strip().split(', ')
        tolympiad = list(input("Введите олимпиаду задачи: "))
        tyear = list(input("Введите год олимпиады: "))
        tlanguage = input(
            "На какой язык составлена задача: ").strip().split(', ')
        searched = db.top_search(
            ttitle,
            tauthors,
            ttags,
            tolympiad,
            tyear,
            tlanguage)
        for t in searched:
            print(f"[{t['id']}] {t['title']} {t['language']}")
    if komanda == 'dai_ti':
        print(db.dai_titles())
    if komanda == 'dai_ol':
        print(db.dai_olympiads())
    if komanda == 'dai_years':
        print(db.dai_years())
    if komanda == 'tpo_au':
        t_au = input('Введите автора: ')
        sp_po_au = db.task_po_author(t_au)
        for t in sp_po_au:
            print(f"[{t['id']}] {t['title']} {t['language']}")
    if komanda == 'tpo_tag':
        t_tag = input('Введите тэг: ')
        sp_po_tag = db.task_po_tag(t_tag)
        for t in sp_po_tag:
            print(f"[{t['id']}] {t['title']} {t['language']}")
    if komanda == 'tpo_lang':
        t_lang = input('Введите язык: ')
        sp_po_lang = db.task_po_lang(t_lang)
        for t in sp_po_lang:
            print(f"[{t['id']}] {t['title']} {t['language']}")
