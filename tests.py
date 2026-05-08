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
        tlanguage = input("На какой язык составлена задача: ")
        tsender_id = 1234567 
        tfile_id = "file_id_test_123" 
        tanswer_file_id = "answer_test_123"
        print("\nПробую сохранить в базу...")
        try:
            db.add_task(tsender_id, ttitle, ttext, tfile_id, tanswer, tanswer_file_id, tauthors, ttags, tolympiad, tyear, tlanguage)
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
    elif komanda == "del":
        print("ТЕСТИРОВАНИЕ УДАЛЕНИЯ ЗАДАЧИ")
        a = input("Введите id задачи, которую хотите удалить: ")
        try:
            db.udalenie(a)
            print("УСПЕШНО! ВЫ УНИЧТОЖИИЛИ ЭТУ ЗАДАЧУ")
        except Exception as e:
            print(f"ОШИБКА при удалении: {e}")
    elif komanda == "dobro":
        print("ТЕСТИРОВАНИЕ ОДОБРЕНИЯ ЗАДАЧИ")
        a = input("Введите id задачи, которую хотите одобрить: ")
        try:
            db.odobrenie(a)
            print("УСПЕШНО! ВЫ ОДОБРИЛИ ЭТУ ЗАДАЧУ")
        except Exception as e:
            print(f"ОШИБКА при одобрение: {e}")