import asyncio
import uuid
import os

from create_bot import bot, dp
from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from db import dai_authors, dai_olympiads, dai_lang, dai_tags, add_task
from db import top_search

step = {}
answers = {}

start_router = Router()

#НАЧАЛО ПОИСКА ЗАДАЧИ
search_step = {}      # этап поиска: 'choosing_params', 'asking_name', 'asking_year' и т.д.
search_params = {}    # выбранные пользователем параметры (список)
search_values = {}    # значения параметров (словарь: ключ -> список значений)
search_index = {}     # индекс текущего параметра, который спрашиваем
search_results = {}   # результаты поиска для каждого пользователя`
search_current_index = {}   # текущий индекс в результатах поиска для навигации

def make_params_keyboard(selected_params): #Клавиатура для выбора параметров поиска
    all_params = {
        "name": "Название задачи",
        "authors": "Авторы",
        "tags": "Теги",
        "olympiad": "Олимпиада",
        "year": "Год",
        "language": "Язык"
    }
    
    buttons = []
    for param_key, param_label in all_params.items():
        if param_key in selected_params:
            button_text = f"✅ {param_label}"
        else:
            button_text = f"⬜ {param_label}"
        buttons.append([InlineKeyboardButton(text=button_text, callback_data=f"select_{param_key}")])
    
    # Кнопки действий
    buttons.append([InlineKeyboardButton(text="Начать поиск", callback_data="start_search")])
    buttons.append([InlineKeyboardButton(text="Отмена", callback_data="cancel_search")])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def make_cancel_keyboard(): #Клавиатура для отмены поиска
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Отменить поиск", callback_data="cancel_search")]
    ])
    return keyboard

def results_keyboard(results, current_index): #Клавиатура для навигации по результатам поиска"
    buttons = []
    if current_index > 0:
        buttons.append(InlineKeyboardButton(text="Назад", callback_data="prev_result"))
    if current_index < len(results) - 1:
        buttons.append(InlineKeyboardButton(text="Вперед", callback_data="next_result"))
    buttons.append(InlineKeyboardButton(text="Завершить поиск", callback_data="cancel_search"))
    return InlineKeyboardMarkup(inline_keyboard=[buttons])

@start_router.message(Command('search'))
async def cmd_search(message: Message):
    """Начало поиска: выбор параметров"""
    user_id = message.from_user.id
    print(f"DEBUG: /search вызван, user_id={user_id}") 
    
    search_step[user_id] = "choosing_params"
    search_params[user_id] = []
    
    await message.answer(
        "Поиск задачи\n\n"
        "Выбери параметры, которые ты помнишь о задаче.\n"
        "Можно выбрать несколько. Нажми на параметр, чтобы добавить или убрать его.\n\n"
        "Когда выберешь всё, что помнишь, нажми «Начать поиск».",
        parse_mode="Markdown",
        reply_markup=make_params_keyboard([])
    )

async def handle_search_callbacks(callback: CallbackQuery): #Обрабатывает все коллбеки от кнопок поиска
    user_id = callback.from_user.id
    data = callback.data
    
    # Если пользователь не в режиме поиска — игнорируем
    if user_id not in search_step:
        await callback.answer("Сначала введи /search")
        return
    
    # Отмена поиска
    if data == "cancel_search":
        # Очищаем все данные пользователя
        if user_id in search_step:
            del search_step[user_id]
        if user_id in search_params:
            del search_params[user_id]
        if user_id in search_values:
            del search_values[user_id]
        if user_id in search_index:
            del search_index[user_id]
        
        await callback.message.edit_reply_markup(None)
        await callback.message.answer("Поиск отменён. Используй /search для нового поиска.")
        await callback.answer()
        return
    
    #Выбор параметра
    if data.startswith("select_"):
        param = data.replace("select_", "")
        
        if param in search_params[user_id]:
            search_params[user_id].remove(param)
            await callback.answer(f"Убран параметр: {param}")
        else:
            search_params[user_id].append(param)
            await callback.answer(f"Добавлен параметр: {param}")
        
        # Обновляем клавиатуру
        await callback.message.edit_reply_markup(
            reply_markup=make_params_keyboard(search_params[user_id])
        )
        return
    
    #Начало поиска
    if data == "start_search":
        if not search_params[user_id]:
            await callback.answer("Выбери хотя бы один параметр!")
            return
        
        #Инициализируем сбор значений
        search_values[user_id] = {}
        search_index[user_id] = 0
        
        #Убираем клавиатуру выбора параметров
        await callback.message.edit_reply_markup(None)
        
        #Начинаем опрос параметров
        await ask_next_param(callback.message, user_id)
        await callback.answer()
        return

async def ask_next_param(message: Message, user_id: int): #Спрашивает пользователя о значении следующего параметра
    params_list = search_params[user_id]
    current_index = search_index[user_id]
    
    #Если все параметры уже опрошены — запускаем поиск
    if current_index >= len(params_list):
        await perform_search(message, user_id)
        return
    
    #Какой параметр сейчас спрашиваем
    current_param = params_list[current_index]
    
    #Словарь с понятными названиями параметров и пояснениями
    param_info = {
        "name": ("название задачи", "Введи название задачи (можно часть слова)"),
        "authors": ("авторов", "Введи авторов через запятую (например: Иванов, Петрова)"),
        "tags": ("теги", "Введи теги через запятую (например: фонетика, морфология)"),
        "olympiad": ("олимпиаду", "Введи название олимпиады"),
        "year": ("год", "Введи год (например: 2024)"),
        "language": ("язык", "Введи язык или языки через запятую (например: русский, английский)")
    }
    
    param_name, prompt_text = param_info.get(current_param, (current_param, "Введи значение"))
    
    # Сохраняем в step, какой параметр сейчас опрашиваем
    search_step[user_id] = f"asking_{current_param}"
    
    await message.answer(
        f"*Вопрос {current_index + 1} из {len(params_list)}*\n\n"
        f"Ты выбрал параметр: *{param_name}*\n\n"
        f"{prompt_text}",
        parse_mode="Markdown",
        reply_markup=make_cancel_keyboard()
    )

async def handle_search_input(message: Message): # Обрабатывает текстовые ответы пользователя на вопросы о параметрах
    user_id = message.from_user.id
    
    # Проверяем, в режиме ли поиска
    if user_id not in search_step:
        return
    
    step = search_step[user_id]
    
    # Если мы в процессе опроса параметров
    if step.startswith("asking_"):
        current_param = step.replace("asking_", "")
        
        # Получаем введённый текст
        raw_value = message.text.strip()
        
        if not raw_value:
            await message.answer("Пожалуйста, введи значение.", reply_markup=make_cancel_keyboard())
            return
        
        # Преобразуем ввод в список в зависимости от типа параметра
        if current_param in ["authors", "tags", "language"]:
            # Для этих параметров разбиваем по запятым и чистим пробелы
            value_list = [item.strip() for item in raw_value.split(",") if item.strip()]
        elif current_param == "year":
            # Для года проверяем, что это число
            try:
                year = int(raw_value)
                # Базовая проверка на разумность года
                if 1800 <= year <= 2030:
                    value_list = [year]
                else:
                    await message.answer(
                        "Год должен быть в диапазоне от 1800 до 2030. Попробуй ещё раз.",
                        reply_markup=make_cancel_keyboard()
                    )
                    return
            except ValueError:
                await message.answer(
                    "Пожалуйста, введи год числом (например: 2024).",
                    reply_markup=make_cancel_keyboard()
                )
                return
        else:
            # Для name и olympiad — просто строка в списке
            value_list = [raw_value]
        
        # Сохраняем значение в словарь
        search_values[user_id][current_param] = value_list
        
        # Переходим к следующему параметру
        search_index[user_id] += 1
        
        # Спрашиваем следующий параметр или запускаем поиск
        await ask_next_param(message, user_id)
        return

async def perform_search(message: Message, user_id: int):
    """
    Выполняет поиск с собранными значениями параметров
    """
    # Получаем словарь со значениями всех параметров
    values_dict = search_values[user_id]
    
    # Важно: нужно создать словарь со ВСЕМИ параметрами (даже теми, что не выбраны), для невыбранных параметров значение = None
    all_params = {
        "name": None,
        "authors": None,
        "tags": None,
        "olympiad": None,
        "year": None,
        "language": None
    }
    
    # Заполняем только те параметры, которые пользователь указал
    for param, value_list in values_dict.items():
        all_params[param] = value_list
    
    # Показываем пользователю, что ищем
    status_message = await message.answer("Ищу задачи в базе данных... Подожди немного.")
    
    try:
        # Вызываем функцию поиска из db.py
        # top_search должна принимать словарь вида {param: [values] или None}
        results = top_search(all_params)
        
        # Удаляем сообщение "Ищу..."
        await status_message.delete()
        
        if not results:
            await message.answer(
                "*Задачи не найдены*\n\n"
                "Попробуй:\n"
                "• выбрать другие параметры\n"
                "• использовать /search для нового поиска",
                parse_mode="Markdown"
            )
        else:
            # Показываем результаты (топ-5)
            current_index = 0
            for t in results:
                current_index += 1
                if current_index > 5:
                    break
                await message.answer(
                    f"*Результат {current_index} из {len(results)}:*\n\n"
                    f"Название: {t['name']}\n" if t['name'] else "Название: Не указано\n" +
                    f"Авторы: {', '.join(t['authors']) if t['authors'] else 'Не указаны'}\n" +
                    f"Теги: {', '.join(t['tags']) if t['tags'] else 'Нет тегов'}\n" +
                    f"Олимпиада: {t['olympiad'] if t['olympiad'] else 'Не указана'}\n" +
                    f"Год: {t['year'] if t['year'] else 'Не указан'}\n" +
                    f"Язык: {t['language'] if t['language'] else 'Не указан'}", reply_markup=results_keyboard(results, current_index))
    except Exception as e:
        await status_message.delete()
        await message.answer(f"Ошибка при поиске: {str(e)}")
    
    finally:
        # Очищаем все данные поиска для пользователя
        if user_id in search_step:
            del search_step[user_id]
        if user_id in search_params:
            del search_params[user_id]
        if user_id in search_values:
            del search_values[user_id]
        if user_id in search_index:
            del search_index[user_id]
#КОНЕЦ ПОИСКА ЗАДАЧИ

def files_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Загрузить файл", callback_data="file")], [InlineKeyboardButton(text="Ввести текстом", callback_data="text")]
    ])
    return keyboard
#кнопка скипа
def skip_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Пропустить", callback_data="skip")], [InlineKeyboardButton(text="Назад", callback_data="back")]
    ])
    return keyboard
#кнопка назад
def back_keyboard(buttons):
    buttons.append([InlineKeyboardButton(text="Назад", callback_data="back")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

#клавиатура только назад
def onlyback_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Назад", callback_data="back")]
    ])
    return keyboard

#клавиатура без кнопки скипа и с единичным выбором
def noskip_onetag_keyboard(tags_db, chosen_tag):
    buttons = []

    for tag in tags_db:
        if tag == chosen_tag:
            chosen = f"✅{tag}"
        else:
            chosen = tag
        buttons.append([InlineKeyboardButton(text=chosen, callback_data=f"one_{tag}")])
    lower_row = [InlineKeyboardButton(text="Готово", callback_data="done"), InlineKeyboardButton(text="Нет в списке", callback_data="custom_tag")]
    buttons.append(lower_row)
    return back_keyboard(buttons)

def tags_keyboard(tags_db, chosen_tags):
    buttons = []

    for tag in tags_db:
        if tag in chosen_tags:
            chosen = f"✅{tag}"
        else:
            chosen = tag
        buttons.append([InlineKeyboardButton(text=chosen, callback_data=f"tag_{tag}")])
    
    lower_row = [InlineKeyboardButton(text="Готово", callback_data="done"), InlineKeyboardButton(text="Пропустить", callback_data="skip"), InlineKeyboardButton(text="Нет в списке", callback_data="custom_tag")]
    buttons.append(lower_row)
    return back_keyboard(buttons)

async def handle_tags(callback: CallbackQuery, user_id: int):
    data = callback.data
    info = answers[user_id].get('info')
    custom = answers[user_id].get('custom')
    next = answers[user_id].get('next')
    tags_db = answers[user_id].get('tags_db')
    
    if not info:
        return
    if step.get(user_id) == 3.1:
        if data.startswith('one_'):
            tag = data[4: ]
            answers[user_id]['olympiad'] = tag
            tags_db = answers[user_id].get('tags_db', [])
            await callback.message.edit_reply_markup(reply_markup=noskip_onetag_keyboard(tags_db, tag))
            await callback.answer(f'Выбрана олимпиада"{tag}".')
        elif data == 'custom_tag':
            step[user_id] = 3.2
            await callback.message.edit_reply_markup(None)
            await callback.message.answer(f'Введите название олимпиады.', reply_markup=onlyback_keyboard())
            await callback.answer()
        elif data == 'done':
            if not answers[user_id].get('olympiad') and not answers[user_id].get('custom_olympiad'):
                await callback.answer('Пожалуйста, выберите олимпиаду или нажмите "Нет в списке".')
                return
            answers[user_id]['olympiad'] = answers[user_id]['olympiad'] if answers[user_id].get('olympiad') else answers[user_id].get('custom_olympiad')

            if 'custom_olympiad' in answers[user_id]:
                del answers[user_id]['custom_olympiad']
            if 'tags_db' in answers[user_id]:
                del answers[user_id]['tags_db']
            if 'info' in answers[user_id]:
                del answers[user_id]['info']
            if 'custom' in answers[user_id]:
                del answers[user_id]['custom']
            if 'next' in answers[user_id]:
                del answers[user_id]['next']
            step[user_id] = 4
            await callback.message.edit_reply_markup(None)
            await get_tags4(callback.message, user_id)
            await callback.answer() 
        return
    elif data.startswith('tag_'):
        tag = data[4: ]
        if tag in answers[user_id][info]:
            answers[user_id][info].remove(tag)
            await callback.answer(f'Тег "{tag}" удалён.')
        else:
            answers[user_id][info].append(tag)
            await callback.answer(f'Тег "{tag}" добавлен.')
        await callback.message.edit_reply_markup(reply_markup=tags_keyboard(tags_db, answers[user_id][info]))
    elif data == 'custom_tag':
        step[user_id] = round(step[user_id] + 0.1, 1)
        await callback.message.edit_reply_markup(None)
        await callback.message.answer(f'Введите свои варианты для "{info}" через запятую, если их несколько.', reply_markup=onlyback_keyboard())
        await callback.answer()

    elif data == "done":
        all = list(set(answers[user_id].get(custom, []) + answers[user_id].get(info, [])))
        answers[user_id][info] = all
        if not answers[user_id][info]:
            await callback.answer('Пожалуйста, выберите хотя бы один тег или нажмите "Пропустить".')
            return

        if custom in answers[user_id]:
            del answers[user_id][custom]
        if 'tags_db' in answers[user_id]:
            del answers[user_id]['tags_db']
        if 'info' in answers[user_id]:
            del answers[user_id]['info']
        if 'custom' in answers[user_id]:
            del answers[user_id]['custom']
        if 'next' in answers[user_id]:
            del answers[user_id]['next']
        step[user_id] = next
        await callback.message.edit_reply_markup(None)
        await callback.message.answer(f"Выбранные теги: {', '.join(answers[user_id][info])}")
        if next == 2:
            await callback.message.answer('Шаг 2. Добавьте год олимпиады. Если не помните, нажмите "Пропустить", однако тогда вы пропустите также Шаг 3 с указанием олимпиады.', reply_markup=skip_keyboard())
        elif next == 4:
            await get_tags4(callback.message, user_id)
        elif next == 5:
            await get_tags5(callback.message, user_id)
        elif next == 6.1:
            await callback.message.answer('Шаг 6. Как вы хотите добавить задачу?', reply_markup=files_keyboard())
        await callback.answer()
    elif data == 'skip':
        answers[user_id][info] = []
        if custom in answers[user_id]:
            del  answers[user_id][custom]
        if 'tags_db' in answers[user_id]:
            del answers[user_id]['tags_db']
        if 'info' in answers[user_id]:
            del answers[user_id]['info']
        if 'custom' in answers[user_id]:
            del answers[user_id]['custom']
        if 'next' in answers[user_id]:
            del answers[user_id]['next']
        
        step[user_id] = next
        await callback.message.edit_reply_markup(None)

        if next == 2:
            await callback.message.answer('Шаг 2. Добавьте год олимпиады. Если не помните, нажмите "Пропустить", однако тогда вы пропустите также Шаг 3 с указанием олимпиады.', reply_markup=skip_keyboard())
        elif next == 4:
            await get_tags4(callback.message, user_id)
        elif next == 5:
            await get_tags5(callback.message, user_id)
        elif next == 6.1:
            await callback.message.answer('Шаг 6. Как вы хотите добавить задачу?', reply_markup=files_keyboard())
        await callback.answer()

#начало
@start_router.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer('Привет! Это база лингвистических задач, в которой ты можешь найти задания по ключевым словам, автору, олимпиаде и т. п. Пиши /add, чтобы добавить задачу, или /search, чтобы найти задачу.')

@start_router.message(Command('add'))
async def cmd_add(message: Message):
    user_id = message.from_user.id
    step[user_id] = 0
    await message.answer('Шаг 0. Введите название задачи. Если не хотите указывать, нажмите "Пропустить".', reply_markup=skip_keyboard())

#все коллбеки
@start_router.callback_query()
async def callbacks(callback: CallbackQuery):
    user_id = callback.from_user.id
    data = callback.data

    if user_id in search_step:
        await handle_search_callbacks(callback)
        return

    if data == "back":
        if user_id not in step:
            await callback.answer()
            return
        elif step[user_id] == 0:
            del step[user_id]
            if user_id in answers:
                del answers[user_id]
            await callback.message.edit_reply_markup(None)
            await callback.message.answer('Вы вернулись в главное меню. Пишите /add, чтобы добавить задачу, или /search, чтобы найти задачу.', reply_markup=None)
            await callback.answer()
            return
        elif step[user_id] in [1, 1.1]:
            step[user_id] = 0
            if 'authors' in answers[user_id]:
                del answers[user_id]['authors']
            if 'custom_authors' in answers[user_id]:
                del answers[user_id]['custom_authors']
            await callback.message.edit_reply_markup(None)
            await callback.message.answer('Шаг 0. Введите название задачи. Если не хотите указывать, нажмите "Пропустить".', reply_markup=skip_keyboard())
            await callback.answer()
            return
        elif step[user_id] == 2:
            step[user_id] = 1
            if 'year' in answers[user_id]:
                del answers[user_id]['year']
            await callback.message.edit_reply_markup(None)
            await get_tags1(callback.message, user_id)
            await callback.answer()
            return
        elif step[user_id] in [3, 3.1, 3.2]:
            step[user_id] = 2
            if 'olympiad' in answers[user_id]:
                del answers[user_id]['olympiad']
            if 'custom_olympiad' in answers[user_id]:
                del answers[user_id]['custom_olympiad']
            await callback.message.edit_reply_markup(None)
            await callback.message.answer('Шаг 2. Добавьте год олимпиады. Если не помните, нажмите "Пропустить", однако тогда вы пропустите также Шаг 3 с указанием олимпиады.', parse_mode='Markdown', reply_markup=skip_keyboard())
            await callback.answer()
            return
        elif step[user_id] in [4, 4.1, 4.2]:
            if answers[user_id].get('year') is None:
                step[user_id] = 2
                await callback.message.edit_reply_markup(None)
                await callback.message.answer('Шаг 2. Добавьте год олимпиады. Если не помните, нажмите "Пропустить", однако тогда вы пропустите также Шаг 3 с указанием олимпиады.', parse_mode='Markdown', reply_markup=skip_keyboard())
                await callback.answer()
            else:
                step[user_id] = 3
                await callback.message.edit_reply_markup(None)
                await get_tags3(callback.message, user_id)
                await callback.answer()
            if 'language' in answers[user_id]:
                del answers[user_id]['language']
            if 'custom_language' in answers[user_id]:
                del answers[user_id]['custom_language']

            await callback.answer()
            return
        elif step[user_id] in [5, 5.1, 5.2]:
            step[user_id] = 4
            if 'tags' in answers[user_id]:
                del answers[user_id]['tags']
            if 'customs' in answers[user_id]:
                del answers[user_id]['customs']
            await callback.message.edit_reply_markup(None)
            await get_tags4(callback.message, user_id) 
            await callback.answer()
            return
        elif step[user_id] in [6, 6.1, 6.2, 6.3]:
            step[user_id] = 5
            await callback.message.edit_reply_markup(None)
            await get_tags5(callback.message, user_id)
            await callback.answer()
            return

    if data == "skip":
        if user_id not in answers:
            answers[user_id] = {}
        if step[user_id] == 0:
            answers[user_id]['name'] = None
            step[user_id] = 1
            await callback.message.edit_reply_markup(None)
            await get_tags1(callback.message, user_id)
            await callback.answer()
            return
        if step[user_id] == 1:
            answers[user_id]['authors'] = []
            if 'custom_authors' in answers[user_id]:
                del answers[user_id]['custom_authors']
            await callback.message.edit_reply_markup(None)
            step[user_id] = 2
            await callback.message.answer('Шаг 2. Добавьте год олимпиады. Если не помните, нажмите "Пропустить", однако тогда вы пропустите также Шаг 3 с указанием олимпиады.', parse_mode='Markdown', reply_markup=skip_keyboard())
        elif step[user_id] == 2:
            answers[user_id]['year'] = None
            await callback.message.edit_reply_markup(None)
            step[user_id] = 4
            await get_tags4(callback.message, user_id)
        elif step[user_id] == 4:
            answers[user_id]['language'] = []
            await callback.message.edit_reply_markup(None)
            step[user_id] = 5
            await get_tags5(callback.message, user_id) 

        elif step[user_id] == 1.1:
            answers[user_id]['authors'] = []
            await callback.message.edit_reply_markup(None)
            if 'custom_authors' in answers[user_id]:
                del answers[user_id]['custom_authors']
            await callback.answer()
            step[user_id] = 2
            await callback.message.answer('Шаг 2. Добавьте год олимпиады. Если не помните, нажмите "Пропустить", однако тогда вы пропустите также Шаг 3 с указанием олимпиады.', parse_mode='Markdown', reply_markup=skip_keyboard())
            return
        elif step[user_id] == 4.1:
            answers[user_id]['language'] = []
            await callback.message.edit_reply_markup(None)
            if 'custom_language' in answers[user_id]:
                del answers[user_id]['custom_language']
            await callback.answer()
            step[user_id] = 5
            await get_tags5(callback.message, user_id) 
            return
        elif step[user_id] == 5.1:
            answers[user_id]['tags'] = []
            await callback.message.edit_reply_markup(None)
            if 'customs' in answers[user_id]:
                del answers[user_id]['customs']
            await callback.answer()
            step[user_id] = 6.1
            await callback.message.answer('Шаг 6. Как вы хотите добавить задачу?', reply_markup=files_keyboard())
            return

    elif step.get(user_id) == 1.1:
        await handle_tags(callback, user_id)
    elif step.get(user_id) == 3.1:
        await handle_tags(callback, user_id)
    elif step.get(user_id) == 4.1:
        await handle_tags(callback, user_id)
    elif step.get(user_id) == 5.1:
        await handle_tags(callback, user_id)
    elif step.get(user_id) == 6.1:
        if data == "file":
            step[user_id] = 6.2
            await callback.message.edit_reply_markup(None)
            await callback.message.answer('Пожалуйста, отправьте файл с задачей.', reply_markup=onlyback_keyboard())
        elif data == "text":
            step[user_id] = 6.3
            await callback.message.edit_reply_markup(None)
            await callback.message.answer('Пожалуйста, введите текст задачи.', reply_markup=onlyback_keyboard())
        elif data == 'back':
            step[user_id] = 5
            await callback.message.edit_reply_markup(None)
            await get_tags5(callback.message, user_id)
        return
    elif step.get(user_id) == 7.1:
        if data == 'file':
            step[user_id] = 7.2
            await callback.message.edit_reply_markup(None)
            await callback.message.answer('Пожалуйста, отправьте файл с ответом.', reply_markup=onlyback_keyboard())
        elif data == 'text':
            step[user_id] = 7.3
            await callback.message.edit_reply_markup(None)
            await callback.message.answer('Пожалуйста, введите текст ответа.', reply_markup=onlyback_keyboard())
        elif data == 'back':
            step[user_id] = 6.1
            await callback.message.edit_reply_markup(None)
            await callback.message.answer('Шаг 6. Как вы хотите добавить задачу?', reply_markup=files_keyboard())
        return
    await callback.answer()
    return

async def get_tags1(message: Message, user_id: int):
    tags_db = dai_authors() #авторы из бд
    if user_id not in answers:
        answers[user_id] = {}
    if 'authors' not in answers[user_id]:
        answers[user_id]['authors'] = []
    if 'custom_authors' not in answers[user_id]:
        answers[user_id]['custom_authors'] = []
    
    answers[user_id]['tags_db'] = tags_db
    answers[user_id]['info'] = 'authors'
    answers[user_id]['custom'] = 'custom_authors'
    answers[user_id]['next'] = 2

    step[user_id] = 1.1
    await message.answer('Шаг 1. Выберите авторов задачи из списка. Если не хотите указывать, нажмите "Пропустить".', reply_markup=tags_keyboard(tags_db, answers[user_id]['authors']))

async def get_tags3(message: Message, user_id: int):
    tags_db = dai_olympiads() #олимпиады из бд
    if user_id not in answers:
        answers[user_id] = {}
    if 'olympiad' not in answers[user_id]:
        answers[user_id]['olympiad'] = None
    if 'custom_olympiad' not in answers[user_id]:
        answers[user_id]['custom_olympiad'] = None
    
    answers[user_id]['tags_db'] = tags_db
    answers[user_id]['info'] = 'olympiad'
    answers[user_id]['custom'] = 'custom_olympiad'
    answers[user_id]['next'] = 4

    step[user_id] = 3.1
    await message.answer('Шаг 3. Выберите олимпиаду, на которой встретилась задача, из списка. Этот шаг обязателен, так как вы указали год.', reply_markup=noskip_onetag_keyboard(tags_db, answers[user_id]['olympiad']))

async def get_tags4(message: Message, user_id: int):
    tags_db = dai_lang() #языки из бд
    if user_id not in answers:
        answers[user_id] = {}
    if 'language' not in answers[user_id] or answers[user_id]['language'] is None:
        answers[user_id]['language'] = []
    if 'custom_language' not in answers[user_id]:
        answers[user_id]['custom_language'] = []

    answers[user_id]['tags_db'] = tags_db
    answers[user_id]['info'] = 'language'
    answers[user_id]['custom'] = 'custom_language'
    answers[user_id]['next'] = 5

    step[user_id] = 4.1
    await message.answer('Шаг 4. Выберите из списка язык, которому посвящена задача. Если не хотите указывать, нажмите "Пропустить".', reply_markup=tags_keyboard(tags_db, answers[user_id]['language']))

async def get_tags5(message: Message, user_id: int):
    tags_db = dai_tags() #теги из бд
    if user_id not in answers:
        answers[user_id] = {}
    if 'tags' not in answers[user_id]:
        answers[user_id]['tags'] = []
    if 'customs' not in answers[user_id]:
        answers[user_id]['customs'] = []
    
    answers[user_id]['tags_db'] = tags_db
    answers[user_id]['info'] = 'tags'
    answers[user_id]['custom'] = 'customs'
    answers[user_id]['next'] = 6.1

    step[user_id] = 5.1
    await message.answer('Шаг 5. Выберите теги, связанные с задачей. Если не хотите указывать, нажмите "Пропустить".', reply_markup=tags_keyboard(tags_db, answers[user_id]['tags']))

@start_router.message()
async def answer_message(message: Message):
    user_id = message.from_user.id

    if user_id in search_step:
        await handle_search_input(message)
        return

    if user_id not in step:
        return  # Если пользователь не начал процесс добавления, игнорируем сообщение

    text = message.text
    if step[user_id] == 0:
        if user_id not in answers:
            answers[user_id] = {}
        if text.strip():
            answers[user_id]['name'] = text.strip()
        else:
            answers[user_id]['name'] = None
        step[user_id] = 1
        await get_tags1(message, user_id)
        return

    if step[user_id] == 1:
        await get_tags1(message, user_id)
    elif step[user_id] == 2:
        if text.isdigit():
            year = int(text)            
            if 1750 <= year <= 2050:  
                answers[user_id]['year'] = year
                step[user_id] = 3
                await get_tags3(message, user_id)
            else:
                await message.answer('Пожалуйста, введите корректный год.')
        else:
            await message.answer('Пожалуйста, введите год числом.')
    elif step[user_id] == 3:
        await get_tags3(message, user_id)
    elif step[user_id] == 4:
        await get_tags4(message, user_id)
    elif step[user_id] == 5:
        await get_tags5(message, user_id)
    elif step[user_id] == 1.2:
        answers[user_id]['custom_authors'] = [tag.strip() for tag in text.split(',')]

        step[user_id] = 1.1
        await get_tags1(message, user_id)
        return
    elif step[user_id] == 3.2:
        if 'olympiad' in answers[user_id]:
            del answers[user_id]['olympiad']

        answers[user_id]['custom_olympiad'] = text.strip()

        await message.answer(f'Вы указали олимпиаду "{text.strip()}". Если это верно, нажмите "Готово". Если вы хотите указать другую, выберите ее из списка.')

        step[user_id] = 3.1
        await get_tags3(message, user_id)
        return
    elif step[user_id] == 4.2:
        answers[user_id]['custom_language'] = [tag.strip() for tag in text.split(',')]

        step[user_id] = 4.1
        await get_tags4(message, user_id)
        return
    elif step[user_id] == 5.2:
        answers[user_id]['customs'] = [tag.strip() for tag in text.split(',')]

        step[user_id] = 5.1
        await get_tags5(message, user_id)
        return
    elif step[user_id] == 6.2:
        if message.document is not None:
            answers[user_id]['task_file_id'] = message.document.file_id
            answers[user_id]['task_text'] = None
            step[user_id] = 7.1
            await message.answer('Шаг 7. Как вы хотите добавить ответ на задачу?', reply_markup=files_keyboard())
        else:
            await message.answer('Пожалуйста, отправьте файл с задачей.', reply_markup=onlyback_keyboard())
        return
    elif step[user_id] == 6.3:
        task_text = message.text.strip()
        if not task_text:
            await message.answer('Пожалуйста, введите текст задачи.', reply_markup=onlyback_keyboard())
            return
        answers[user_id]['task_text'] = task_text
        answers[user_id]['task_file_id'] = None
        step[user_id] = 7.1
        await message.answer('Шаг 7. Как вы хотите добавить ответ на задачу?', reply_markup=files_keyboard())
        return
    elif step[user_id] == 7.2:
        if message.document is not None:
            answers[user_id]['answer_file_id'] = message.document.file_id
            answers[user_id]['answer_text'] = None
            await taskfile(message, user_id)
        else:
            await message.answer('Пожалуйста, отправьте файл с ответом.', reply_markup=onlyback_keyboard())
        return
    elif step[user_id] == 7.3:
        answer_text = message.text.strip()
        if not answer_text:
            await message.answer('Пожалуйста, введите текст ответа.', reply_markup=onlyback_keyboard())
            return
        answers[user_id]['answer_text'] = answer_text
        answers[user_id]['answer_file_id'] = None
        await taskfile(message, user_id)
        return

#задача может быть введена с клавы (строка). ограничение по символам какое-то (пять строк?). (это еще будет написано)

async def taskfile(message: Message, user_id: int, is_file=True):
    task_data = answers[user_id].copy()

    sender_id = user_id
    title = task_data.get('name')
    task_text = task_data.get('task_text')
    task_file_id = task_data.get('task_file_id')
    answer_text = task_data.get('answer_text')
    answer_file_id = task_data.get('answer_file_id')
    authors = task_data.get('authors')
    if isinstance(authors, list):
        authors = ', '.join(authors)
    tags = task_data.get('tags')
    if isinstance(tags, list):
        tags = ', '.join(tags)
    olympiad = task_data.get('olympiad')
    year = task_data.get('year')
    language = task_data.get('language')
    if isinstance(language, list):
        language = ', '.join(language)
    
    add_task(sender_id, title, task_text, task_file_id, answer_text, answer_file_id, authors, tags, olympiad, year, language)

    await message.answer('Спасибо! Ваша задача добавлена в базу данных.')
    if user_id in step:
        del step[user_id]
    if user_id in answers:
        del answers[user_id]

#запуск бота
async def main():
    dp.include_router(start_router)
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())