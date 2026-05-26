import asyncio
import uuid
import os
import re
import sqlite3

from create_bot import bot, dp, admins
from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import FSInputFile
from aiogram.types import Message
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from db import task_po_id, dai_authors, dai_olympiads, dai_lang, dai_tags, add_task, top_search, vivod_na_check, DB
from admin import admin

from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

class SearchStates(StatesGroup):
    waiting_for_id = State()

adm = admins

step = {}
answers = {}

start_router = Router()

#НАЧАЛО ПОИСКА ЗАДАЧИ
search_step = {}      
search_params = {}  
search_values = {}
search_index = {}
search_results = {}
search_current_index = {}


def escape_markdown_v2(text: str) -> str:
    special_chars = r'([_*\[\]()~`>#+\-=|{}.!])'
    return re.sub(special_chars, r'\\\1', text)

#клавиатура для выбора параметров поиска
def make_params_keyboard(selected_params): 
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

#клавиатура для отмены поиска
def make_cancel_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Отменить поиск", callback_data="cancel_search")]
    ])
    return keyboard

#новая клавиатура только с кнопкой "Назад"
def make_back_keyboard(): 
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Назад", callback_data="back_to_params")]
    ])
    return keyboard

def make_single_choice_keyboard(items, chosen_item): #для единичного выбора олимпиады
    buttons = []
    for item in items:
        if item == chosen_item:
            button_text = f"✅ {item}"
        else:
            button_text = f"⬜ {item}"
        buttons.append([InlineKeyboardButton(text=button_text, callback_data=f"choose_olympiad_{item}")])

    lower_row = [InlineKeyboardButton(text="Готово", callback_data="done_olympiad"), 
                 InlineKeyboardButton(text="Пропустить", callback_data="skip_olympiad"),
                 InlineKeyboardButton(text="Назад", callback_data="back_to_params")]
    buttons.append(lower_row)
    return InlineKeyboardMarkup(inline_keyboard=buttons)

#функция для множественного выбора (авторы, теги, языки)
def multi_choice_keyboard(items, chosen_items, param_type):
    buttons = []
    for item in items:
        if item in chosen_items:
            button_text = f"✅ {item}"
        else:
            button_text = f"⬜ {item}"
        buttons.append([InlineKeyboardButton(text=button_text, callback_data=f"choose_multi_{param_type}_{item}")])
    lower_row = []
    if chosen_items:
        lower_row.append(InlineKeyboardButton(text="Готово", callback_data=f"done_multi_{param_type}"))
    lower_row.append(InlineKeyboardButton(text="Пропустить", callback_data=f"skip_multi_{param_type}"))
    lower_row.append(InlineKeyboardButton(text="Назад", callback_data="back_to_params"))
    buttons.append(lower_row)
    return InlineKeyboardMarkup(inline_keyboard=buttons)

#клавиатура для навигации по результатам поиска"
def results_keyboard(results, current_index): 
    buttons = []
    if current_index > 0:
        buttons.append(InlineKeyboardButton(text="Назад", callback_data="prev_result"))
    if current_index < len(results) - 1:
        buttons.append(InlineKeyboardButton(text="Вперед", callback_data="next_result"))
    buttons.append(InlineKeyboardButton(text="Завершить поиск", callback_data="cancel_search"))
    return InlineKeyboardMarkup(inline_keyboard=[buttons])

@start_router.message(Command('search'))
async def cmd_search(message: Message):
    user_id = message.from_user.id   
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

    if user_id not in search_step:
        await callback.answer("Сначала введи /search")
        return
    
    #возврат к выбору параметров
    if data == "back_to_params":
        search_step[user_id] = "choosing_params"
        await callback.message.edit_reply_markup(None)
        await callback.message.answer(
            "Выбери параметры для поиска:",
            reply_markup=make_params_keyboard(search_params[user_id])
        )
        await callback.answer()
        return
    
    #отмена поиска
    if data == "cancel_search":
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
    
    #выбор параметра
    if data.startswith("select_"):
        param = data.replace("select_", "")
        
        if param in search_params[user_id]:
            search_params[user_id].remove(param)
            await callback.answer(f"Убран параметр: {param}")
        else:
            search_params[user_id].append(param)
            await callback.answer(f"Добавлен параметр: {param}")
        
        #обновляем клавиатуру
        await callback.message.edit_reply_markup(
            reply_markup=make_params_keyboard(search_params[user_id])
        )
        return
    
    #обработка выбора олимпиады (единичный выбор)
    if data.startswith("choose_olympiad_"):
        value = data.replace("choose_olympiad_", "")
        search_values[user_id]["olympiad"] = value
        await callback.answer(f"Выбрана олимпиада: {value}")
        
        items = dai_olympiads()
        await callback.message.edit_reply_markup(
            reply_markup=make_single_choice_keyboard(items, value)
        )
        return
    
    #завершение выбора олимпиады
    if data == "done_olympiad":
        if "olympiad" not in search_values[user_id]:
            await callback.answer("Пожалуйста, выберите олимпиаду или нажмите «Пропустить»!")
            return
        search_index[user_id] += 1
        await callback.message.edit_reply_markup(None)
        await next_param(callback.message, user_id)
        await callback.answer()
        return
    
    #пропуск олимпиады
    if data == "skip_olympiad":
        search_values[user_id]["olympiad"] = None
        search_index[user_id] += 1
        await callback.message.edit_reply_markup(None)
        await next_param(callback.message, user_id)
        await callback.answer()
        return
    
    #обработка множественного выбора (авторы, теги, языки)
    if data.startswith("choose_multi_"):
        parts = data.split("_", 3)  #['choose', 'multi', 'authors', 'Иванов']
        if len(parts) >= 4:
            param_type = parts[2]
            value = parts[3]
            
            if param_type not in search_values[user_id]:
                search_values[user_id][param_type] = []
            
            if value in search_values[user_id][param_type]:
                search_values[user_id][param_type].remove(value)
                await callback.answer(f"Убран {param_type}: {value}")
            else:
                search_values[user_id][param_type].append(value)
                await callback.answer(f"Добавлен {param_type}: {value}")
            
            #обновляем клавиатуру
            if param_type == "authors":
                items = dai_authors()
            elif param_type == "tags":
                items = dai_tags()
            else:  # language
                items = dai_lang()
            
            await callback.message.edit_reply_markup(
                reply_markup=multi_choice_keyboard(items, search_values[user_id][param_type], param_type)
            )
        return
    
    #завершение множественного выбора
    if data.startswith("done_multi_"):
        param_type = data.replace("done_multi_", "")
        if param_type not in search_values[user_id]:
            search_values[user_id][param_type] = []
        search_index[user_id] += 1
        await callback.message.edit_reply_markup(None)
        await next_param(callback.message, user_id)
        await callback.answer()
        return
    
    #пропуск множественного выбора
    if data.startswith("skip_multi_"):
        param_type = data.replace("skip_multi_", "")
        search_values[user_id][param_type] = []
        search_index[user_id] += 1
        await callback.message.edit_reply_markup(None)
        await next_param(callback.message, user_id)
        await callback.answer()
        return

    #начало поиска
    if data == "start_search":
        if not search_params[user_id]:
            await callback.answer("Выбери хотя бы один параметр!")
            return
        
        #инициализируем сбор значений
        search_values[user_id] = {}
        search_index[user_id] = 0
        
        #убираем клавиатуру выбора параметров
        await callback.message.edit_reply_markup(None)

        await next_param(callback.message, user_id)
        await callback.answer()
        return

async def next_param(message: Message, user_id: int): #Спрашивает пользователя о значении следующего параметра
    params_list = search_params[user_id]
    current_index = search_index[user_id]
    
    #если все параметры уже опрошены — запускаем поиск
    if current_index >= len(params_list):
        from create_bot import dp
        state = dp.fsm.resolve_context(bot, message.chat.id, user_id)
        await perform_search(message, user_id, state) # <-- Передали его сюда
        return
    current_param = params_list[current_index]
    
    #для олимпиады показываем клавиатуру с единичным выбором
    if current_param == "olympiad":
        items = dai_olympiads()
        chosen = search_values[user_id].get(current_param)
        search_step[user_id] = f"selecting_{current_param}"
        
        await message.answer(
            f"Вопрос {current_index + 1} из {len(params_list)}\n\n"
            f"Вы выбрали параметр: олимпиада\n\n"
            f"Выберите олимпиаду из списка (можно только одну):",
            parse_mode="Markdown",
            reply_markup=make_single_choice_keyboard(items, chosen)
        )
        return
    
    #для авторов, тегов, языков - множественный выбор из кнопок
    if current_param in ["authors", "tags", "language"]:
        if current_param == "authors":
            items = dai_authors()
            title = "авторы"
        elif current_param == "tags":
            items = dai_tags()
            title = "тэги"
        else:  # language
            items = dai_lang()
            title = "язык"
        
        chosen = search_values[user_id].get(current_param, [])
        search_step[user_id] = f"selecting_{current_param}"
        
        await message.answer(
            f"Вопрос {current_index + 1} из {len(params_list)}\n\n"
            f"Вы выбрали параметр: {title}\n\n"
            f"Выберите нужное (можно несколько):",
            parse_mode="Markdown",
            reply_markup=multi_choice_keyboard(items, chosen, current_param)
        )
        return
    
     #для названия и года - текстовый ввод
    param_info = {
        "name": ("название задачи", "Введи название задачи (можно часть слова)"),
        "year": ("год", "Введи год (например: 2024)")
    }
    
    param_name, prompt_text = param_info.get(current_param, (current_param, "Введи значение"))
    
    search_step[user_id] = f"asking_{current_param}"
    
    await message.answer(
        f"Вопрос {current_index + 1} из {len(params_list)}\n\n"
        f"Ты выбрал параметр: {param_name}\n\n"
        f"{prompt_text}",
        parse_mode="Markdown",
        reply_markup=make_back_keyboard()
    )

async def handle_search_input(message: Message): # Обрабатывает текстовые ответы пользователя на вопросы о параметрах
    user_id = message.from_user.id
    
    #проверяем, в режиме ли поиска
    if user_id not in search_step:
        return
    
    step = search_step[user_id]
    
    #если мы в процессе опроса параметров
    if step.startswith("asking_"):
        current_param = step.replace("asking_", "")
        
        #получаем введённый текст
        raw_value = message.text.strip()
        
        if not raw_value:
            await message.answer("Пожалуйста, введи значение.", reply_markup=make_back_keyboard())
            return
        
        #преобразуем ввод в список в зависимости от типа параметра
        if current_param in ["authors", "tags", "language"]:
            #для этих параметров разбиваем по запятым и чистим пробелы
            value_list = [item.strip() for item in raw_value.split(",") if item.strip()]
        elif current_param == "year":
            try:
                year = int(raw_value)
                if 1800 <= year <= 2030:
                    value_list = [year]
                else:
                    await message.answer(
                        "Год должен быть в диапазоне от 1800 до 2030. Попробуй ещё раз.",
                        reply_markup=make_back_keyboard()
                    )
                    return
            except ValueError:
                await message.answer(
                    "Пожалуйста, введи год числом (например: 2024).",
                    reply_markup=make_back_keyboard()
                )
                return
        else:
            #для name — просто строка в списке
            value_list = [raw_value]
        
        search_values[user_id][current_param] = value_list
        search_index[user_id] += 1
        
        #спрашиваем следующий параметр
        await next_param(message, user_id)
        return

#словарь со значениями всех параметров
async def perform_search(message: Message, user_id: int, state: FSMContext):
    values_dict = search_values[user_id]
    all_params = {
        "name": None,
        "authors": None,
        "tags": None,
        "olympiad": None,
        "year": None,
        "language": None
    }
    
    #заполняем только те параметры, которые пользователь указал
    for param, value in values_dict.items():
        if param == "olympiad":
            all_params[param] = [value] if value else None
        else:
            all_params[param] = value
    
    #показываем пользователю, что ищем
    status_message = await message.answer("Ищу задачи в базе данных... Подожди немного.")
    
    try:
        #функция из db.py
        results = top_search(
            all_params["name"],
            all_params["authors"],
            all_params["tags"],
            all_params["olympiad"],
            all_params["year"],
            all_params["language"]
        )
        
        #удаляем сообщение "Ищу..."
        await status_message.delete()
        
        if not results:
            await message.answer(
                "Задачи не найдены\n\n"
                "Попробуй выбрать другие параметры или ипользовать /search для нового поиска",
                )
        else:
            #показываем результаты (топ-5)
            response = f"Найдено задач: {len(results)}\n\n"
            for i, task in enumerate(results[:5], 1):
                task_id = task.get('id', '')
                task_title = task.get('title')
                if not task_title:  #пофиксили None
                    task_title = 'Без названия'
                response += f"{i}. {task_title} (id: {task_id})\n"
                if task.get('authors'):
                    authors_str = ", ".join(task['authors']) if isinstance(task['authors'], list) else task['authors']
                    response += f"Авторы: {authors_str}\n"
                if task.get('olympiad'):
                    response += f"Олимпиада: {task['olympiad']}"
                    if task.get('year'):
                        response += f" ({task['year']})"
                    response += "\n"
                if task.get('language'):
                    langs_str = ", ".join(task['language']) if isinstance(task['language'], list) else task['language']
                    response += f"Язык: {langs_str}\n"
                if task.get('tags'):
                    tags_str = ", ".join(task['tags'][:5]) if isinstance(task['tags'], list) else task['tags']
                    response += f"Теги: {tags_str}\n"
                response += "\n"
            await message.answer(response)
            await message.answer("Введи <b>ID задачи</b> с клавиатуры, чтобы получить её условие и ответ:")
            await state.set_state(SearchStates.waiting_for_id)
            
            #ждём, когда введут айдишник
            search_results[user_id] = results
            search_step[user_id] = "waiting_for_id"
            #убираем всё лишнее
            if user_id in search_params:
                del search_params[user_id]
            if user_id in search_values:
                del search_values[user_id]
            if user_id in search_index:
                del search_index[user_id]
    except Exception as e:
        await status_message.delete()
        await message.answer(f"Ошибка при поиске: {str(e)}")
        for d in [search_step, search_params, search_values, search_index, search_results]:
            if user_id in d:
                del d[user_id] #при ошибке убрать всё, что осталось

@start_router.message(SearchStates.waiting_for_id)
async def process_task_id_input(message: Message, state: FSMContext):
    user_id = message.from_user.id
    
    if not message.text or not message.text.isdigit():
        await message.answer("Пожалуйста, введите корректный числовой ID задачи.")
        return

    task_id = int(message.text)
    task = task_po_id(task_id)

    if not task:
        await message.answer("Задача с таким ID не найдена в нашей базе данных. Попробуйте ещё раз:")
        return

    #очистка
    await state.clear()
    for d in [search_step, search_params, search_values, search_index, search_results]:
        if user_id in d:
            del d[user_id]

    task_data, answer_data = task[0], task[1]

    await message.answer(f"<b>Cодержимое задачи (id: {task_id})</b>")

    #условие
    if not task_data:
        await message.answer("<b>Условие задачи:</b> отсутствует")
    elif " " not in str(task_data) and len(str(task_data)) > 30 and not str(task_data).isalnum():
        await message.answer_document(
            document=task_data,
            caption="<b>Файл с условием задачи:</b>"
        )
    else:
        await message.answer(f"<b>Условие задачи:</b>\n{task_data}")

    #ответ со спойлером (С ПАСХАЛКОЙ ХИ ХА ХЕ)
    if not answer_data:
        await message.answer("<b>Ответ на задачу:</b> Сам думай, дурачина!")

    elif " " not in str(answer_data) and len(str(answer_data)) > 30 and not str(answer_data).isalnum():
        await message.answer_document(
            document=answer_data,
            caption="<b>Файл с ответом на задачу</b>"
        )
    else:
        await message.answer(
            f"<b>Ответ на задачу (нажмите, чтобы посмотреть):</b>\n"
            f"<tg-spoiler>{answer_data}</tg-spoiler>"
        )

    await message.answer("Для нового поиска введите /search")

#КОНЕЦ ПОИСКА ЗАДАЧИ
#листтаскс
listasks_category = {}     
listasks_page = {}         
listasks_items = {}        
listasks_task_page = {}    
listasks_task_items = {}   

def make_pagination_keyboard(items, page, prefix, per_page=10):
    start = page * per_page
    end = start + per_page
    current_items = items[start:end]
    
    inline_keyboard = []
    
    for item in current_items:
        if isinstance(item, dict): 
            text = item['text']
            callback_data = f"show_task_id:{item['id']}"
        else: 
            text = str(item)
            callback_data = f"list_click:{prefix}:{items.index(item)}"
            
        inline_keyboard.append([InlineKeyboardButton(text=text, callback_data=callback_data)])
        
    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton(text="Назад", callback_data=f"list_nav:{prefix}:{page-1}"))
    
    total_pages = (len(items) + per_page - 1) // per_page
    if total_pages > 1:
        nav_row.append(InlineKeyboardButton(text=f"{page+1}/{total_pages}", callback_data="noop"))
        
    if end < len(items):
        nav_row.append(InlineKeyboardButton(text="Вперед", callback_data=f"list_nav:{prefix}:{page+1}"))
        
    if nav_row:
        inline_keyboard.append(nav_row)
        
    if prefix != "menu":
        inline_keyboard.append([InlineKeyboardButton(text="⬅Назад к категориям", callback_data="list_back_to_menu")])
        
    return InlineKeyboardMarkup(inline_keyboard=inline_keyboard)

def escape_markdown_v2(text: str) -> str:
    special_chars = r'([_*\[\]()~`>#+\-=|{}.!])'
    return re.sub(special_chars, r'\\\1', text)

async def full_task(message: Message, task: dict):
    task_id = task.get('id', '')
    title = task.get('title') or 'Без названия'
    
    response = f"{title} (id: {task_id})\n\n"
    if task.get('authors'): response += f"Авторы: {task['authors']}\n"
    if task.get('olympiad'): response += f"Олимпиада: {task['olympiad']} ({task['year'] or '—'})\n"
    if task.get('language'): response += f"Язык: {task['language']}\n"
    if task.get('tags'): response += f"Теги: {task['tags']}\n"
    
    await message.answer(response, parse_mode="Markdown")
    await message.answer("Условие задачи:")
    
    if task.get('task_text'):
        await message.answer(f"{task['task_text']}")
    if task.get('task_file_id'):
        await message.answer_document(document=task['task_file_id'], caption="Файл задачи")
        
    await message.answer("Ответ на задачу:")
    
    if task.get('answer_text'):
        safe_answer = escape_markdown_v2(task['answer_text'])
        await message.answer(f"||{safe_answer}||", parse_mode="MarkdownV2")
    if task.get('answer_file_id'):
        await message.answer_document(document=task['answer_file_id'], caption="Файл ответа")

@start_router.message(Command("listasks"))
async def cmd_listasks(message: Message):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="По тэгам", callback_data="list_cat:tags")],
        [InlineKeyboardButton(text="По олимпиадам", callback_data="list_cat:olympiads")],
        [InlineKeyboardButton(text="По авторам", callback_data="list_cat:authors")],
        [InlineKeyboardButton(text="По языкам", callback_data="list_cat:languages")]
    ])
    await message.answer("Выберите категорию для просмотра задач:", reply_markup=keyboard, parse_mode="Markdown")

@start_router.callback_query(F.data.startswith("list_cat:"))
async def process_list_category(callback: CallbackQuery):
    user_id = callback.from_user.id
    category = callback.data.split(":")[1]
    
    listasks_category[user_id] = category
    listasks_page[user_id] = 0
    
    if category == "tags":
        cleaned_items = dai_tags()
        title_text = "Доступные тэги:"
    elif category == "olympiads":
        cleaned_items = dai_olympiads()
        title_text = "Доступные олимпиады:"
    elif category == "authors":
        cleaned_items = dai_authors()
        title_text = "Доступные авторы:"
    elif category == "languages":
        cleaned_items = dai_lang()
        title_text = "Доступные языки:"
    
    if not cleaned_items:
        await callback.answer("В этой категории пока нет элементов.", show_alert=True)
        return
        
    listasks_items[user_id] = cleaned_items
    kb = make_pagination_keyboard(cleaned_items, page=0, prefix="item")
    await callback.message.edit_text(title_text, reply_markup=kb, parse_mode="Markdown")
    await callback.answer()

@start_router.callback_query(F.data.startswith("list_nav:item:"))
async def process_item_navigation(callback: CallbackQuery):
    user_id = callback.from_user.id
    page = int(callback.data.split(":")[2])
    items = listasks_items.get(user_id, [])
    listasks_page[user_id] = page
    
    kb = make_pagination_keyboard(items, page=page, prefix="item")
    await callback.message.edit_reply_markup(reply_markup=kb)
    await callback.answer()

@start_router.callback_query(F.data.startswith("list_click:item:"))
async def process_item_click(callback: CallbackQuery):
    user_id = callback.from_user.id
    item_index = int(callback.data.split(":")[2])
    
    items = listasks_items.get(user_id, [])
    if item_index >= len(items):
        await callback.answer("Ошибка сессии. Введите /listasks заново.", show_alert=True)
        return
        
    selected_value = items[item_index]
    category = listasks_category.get(user_id)
    
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    col_map = {"tags": "tags", "olympiads": "olympiad", "authors": "authors", "languages": "language"}
    column = col_map.get(category, "tags")
    
    cursor.execute(f"SELECT id, title, olympiad, year FROM tasks WHERE {column} LIKE ? AND status = 'approved'", (f"%{selected_value}%",))
    db_tasks = cursor.fetchall()
    conn.close()

    task_buttons_data = []
    for t in db_tasks:
        btn_text = t['title'].strip() if t['title'] and t['title'].strip() else f"Олимпиада: {t['olympiad'] or 'Олимпиада'} ({t['year'] or '---'})"
        task_buttons_data.append({"id": t['id'], "text": btn_text})
        
    listasks_task_items[user_id] = task_buttons_data
    listasks_task_page[user_id] = 0
    
    kb = make_pagination_keyboard(task_buttons_data, page=0, prefix="task")
    await callback.message.edit_text(f"Задачи по запросу «{selected_value}»:", reply_markup=kb, parse_mode="Markdown")
    await callback.answer()

@start_router.callback_query(F.data.startswith("list_nav:task:"))
async def process_task_navigation(callback: CallbackQuery):
    user_id = callback.from_user.id
    page = int(callback.data.split(":")[2])
    tasks_list = listasks_task_items.get(user_id, [])
    listasks_task_page[user_id] = page
    
    kb = make_pagination_keyboard(tasks_list, page=page, prefix="task")
    await callback.message.edit_reply_markup(reply_markup=kb)
    await callback.answer()

@start_router.callback_query(F.data == "list_back_to_menu")
async def process_back_to_menu(callback: CallbackQuery):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="По тэгам", callback_data="list_cat:tags")],
        [InlineKeyboardButton(text="По олимпиадам", callback_data="list_cat:olympiads")],
        [InlineKeyboardButton(text="По авторам", callback_data="list_cat:authors")],
        [InlineKeyboardButton(text="По языкам", callback_data="list_cat:languages")]
    ])
    await callback.message.edit_text("Выберите категорию для просмотра задач:", reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()

@start_router.callback_query(F.data == "noop")
async def process_noop(callback: CallbackQuery):
    await callback.answer()

@start_router.callback_query(F.data.startswith("show_task_id:"))
async def process_show_task_callback(callback: CallbackQuery):
    task_id = int(callback.data.split(":")[1])
    task = vivod_na_check(task_id)
    
    if not task:
        await callback.answer("Ошибка: Задача не найдена.", show_alert=True)
        return
        
    await callback.message.delete()
    await full_task(callback.message, task)
    await callback.answer()
#конец листтаскс

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
def noskip_onetag_keyboard(tags_db, chosen_tags, page=0, one_page=10):
    total = (len(tags_db) + one_page - 1) // one_page
    start = page * one_page
    end = one_page + start
    tags = tags_db[start:end]
    buttons = []

    for i, tag in enumerate(tags, start=start):
        if tag in chosen_tags:
            chosen = f"✅{tag}"
        else:
            chosen = tag
        buttons.append([InlineKeyboardButton(text=chosen, callback_data=f"one_{i}")])
    row = []
    if page > 0:
        row.append(InlineKeyboardButton(text="Назад", callback_data=f"ol_page_{page-1}"))
    row.append(InlineKeyboardButton(text=f"{page + 1}/{total}", callback_data="dlyakrasoty"))
    if page < total - 1:
        row.append(InlineKeyboardButton(text="Вперед", callback_data=f"ol_page_{page+1}"))
    buttons.append(row)
    lower_row = [InlineKeyboardButton(text="Готово", callback_data="done"), InlineKeyboardButton(text="Нет в списке", callback_data="custom_tag")]
    buttons.append(lower_row)
    return back_keyboard(buttons)

def tags_keyboard(tags_db, chosen_tags, page=0, one_page=10):
    total = (len(tags_db) + one_page - 1) // one_page
    start = page * one_page
    end = one_page + start
    tags = tags_db[start:end]
    buttons = []

    for i, tag in enumerate(tags, start=start):
        if tag in chosen_tags:
            chosen = f"✅{tag}"
        else:
            chosen = tag
        buttons.append([InlineKeyboardButton(text=chosen, callback_data=f"tag_{i}")])

    row = []
    if page > 0:
        row.append(InlineKeyboardButton(text="Назад", callback_data=f"page_{page-1}"))
    row.append(InlineKeyboardButton(text=f"{page + 1}/{total}", callback_data="dlyakrasoty"))
    if page < total - 1:
        row.append(InlineKeyboardButton(text="Вперед", callback_data=f"page_{page+1}"))
    buttons.append(row)

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
    if data.startswith("page_"):
        page = int(data.split("_")[-1])
        answers[user_id]['page'] = page
        await callback.message.edit_reply_markup(reply_markup=tags_keyboard(tags_db, answers[user_id][info], page))
        await callback.answer()
        return
    if data.startswith("ol_page_"):
        page = int(data.split("_")[-1])
        answers[user_id]['page'] = page
        await callback.message.edit_reply_markup(reply_markup=noskip_onetag_keyboard(tags_db, answers[user_id]['olympiad'], page))
        await callback.answer()
        return
    if step.get(user_id) == 3.1:
        if data.startswith('one_'):
            ind = int(data[4: ])
            all = answers[user_id].get('tags_db', [])
            if ind < len(all):
                tag = all[ind]
            else:
                return
            answers[user_id]['olympiad'] = tag
            tags_db = answers[user_id].get('tags_db', [])
            await callback.message.edit_reply_markup(reply_markup=noskip_onetag_keyboard(tags_db, tag))
            await callback.answer(f'Ты выбрал олимпиаду"{tag}".')
        elif data == 'custom_tag':
            step[user_id] = 3.2
            await callback.message.edit_reply_markup(None)
            await callback.message.answer(f'Введи название олимпиады.', reply_markup=onlyback_keyboard())
            await callback.answer()
        elif data == 'done':
            if not answers[user_id].get('olympiad') and not answers[user_id].get('custom_olympiad'):
                await callback.answer('Пожалуйста, выбери олимпиаду или нажми "Нет в списке".')
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
        ind = int(data[4: ])
        all = answers[user_id].get('tags_db', [])
        if ind < len(all):
            tag = all[ind]
        else:
            return
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
        await callback.message.answer(f'Введи свои варианты для "{info}" через запятую, если их несколько.', reply_markup=onlyback_keyboard())
        await callback.answer()

    elif data == "done":
        all = list(set(answers[user_id].get(custom, []) + answers[user_id].get(info, [])))
        answers[user_id][info] = all
        if not answers[user_id][info]:
            await callback.answer('Выбери хотя бы один тег или нажми "Пропустить".')
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
        await callback.message.answer(f"Выбранные тэги: {', '.join(answers[user_id][info])}")
        if next == 2:
            await callback.message.answer('Шаг 2. Добавь год олимпиады. Если не помнишь, нажмите "Пропустить", однако тогда вы пропустите также Шаг 3 с указанием олимпиады.', reply_markup=skip_keyboard())
        elif next == 4:
            await get_tags4(callback.message, user_id)
        elif next == 5:
            await get_tags5(callback.message, user_id)
        elif next == 6.1:
            await callback.message.answer('Шаг 6. Как ты хочешь добавить задачу?', reply_markup=files_keyboard())
        await callback.answer()
    elif data == 'skip':
        answers[user_id][info] = []
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

        if next == 2:
            await callback.message.answer('Шаг 2. Добавь год олимпиады. Если не помнишь, нажми "Пропустить", однако тогда ты пропустишь также Шаг 3 с указанием олимпиады.', reply_markup=skip_keyboard())
        elif next == 4:
            await get_tags4(callback.message, user_id)
        elif next == 5:
            await get_tags5(callback.message, user_id)
        elif next == 6.1:
            await callback.message.answer('Шаг 6. Как ты хочешь добавить задачу?', reply_markup=files_keyboard())
        await callback.answer()

#начало
@start_router.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer('Привет! Это база лингвистических задач, в которой ты можешь найти задания по автору, олимпиаде, году и т. п. Пиши /add, чтобы добавить задачу, или /search, чтобы найти задачу.')

@start_router.message(Command('add'))
async def cmd_add(message: Message):
    user_id = message.from_user.id
    step[user_id] = 0
    await message.answer('Шаг 0. Введи название задачи. Если не хочешь указывать, нажми "Пропустить".', reply_markup=skip_keyboard())

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
            await callback.message.answer('Ты вернулся в главное меню. Пиши /add, чтобы добавить задачу, или /search, чтобы найти задачу.', reply_markup=None)
            await callback.answer()
            return
        elif step[user_id] in [1, 1.1]:
            step[user_id] = 0
            if 'authors' in answers[user_id]:
                del answers[user_id]['authors']
            if 'custom_authors' in answers[user_id]:
                del answers[user_id]['custom_authors']
            await callback.message.edit_reply_markup(None)
            await callback.message.answer('Шаг 0. Введи название задачи. Если не хочешь указывать, нажми "Пропустить".', reply_markup=skip_keyboard())
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
            await callback.message.answer('Шаг 2. Добавь год олимпиады. Если не помнишь, нажми "Пропустить", однако тогда ты пропустишь также Шаг 3 с указанием олимпиады.', parse_mode='Markdown', reply_markup=skip_keyboard())
            await callback.answer()
            return
        elif step[user_id] in [4, 4.1, 4.2]:
            if answers[user_id].get('year') is None:
                step[user_id] = 2
                await callback.message.edit_reply_markup(None)
                await callback.message.answer('Шаг 2. Добавь год олимпиады. Если не помнишь, нажми "Пропустить", однако тогда ты пропустишь также Шаг 3 с указанием олимпиады.', parse_mode='Markdown', reply_markup=skip_keyboard())
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
            await callback.message.answer('Шаг 2. Добавь год олимпиады. Если не помнишь, нажми "Пропустить", однако тогда ты пропустишь также Шаг 3 с указанием олимпиады.', parse_mode='Markdown', reply_markup=skip_keyboard())
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
            await callback.message.answer('Шаг 2. Добавь год олимпиады. Если не помнишь, нажми "Пропустить", однако тогда ты пропустишь также Шаг 3 с указанием олимпиады.', parse_mode='Markdown', reply_markup=skip_keyboard())
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
            await callback.message.answer('Шаг 6. Как ты хочешь добавить задачу?', reply_markup=files_keyboard())
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
            await callback.message.answer('Пожалуйста, отправь файл с задачей.', reply_markup=onlyback_keyboard())
        elif data == "text":
            step[user_id] = 6.3
            await callback.message.edit_reply_markup(None)
            await callback.message.answer('Пожалуйста, введи текст задачи.', reply_markup=onlyback_keyboard())
        elif data == 'back':
            step[user_id] = 5
            await callback.message.edit_reply_markup(None)
            await get_tags5(callback.message, user_id)
        return
    elif step.get(user_id) == 7.1:
        if data == 'file':
            step[user_id] = 7.2
            await callback.message.edit_reply_markup(None)
            await callback.message.answer('Пожалуйста, отправь файл с ответом.', reply_markup=onlyback_keyboard())
        elif data == 'text':
            step[user_id] = 7.3
            await callback.message.edit_reply_markup(None)
            await callback.message.answer('Пожалуйста, введи текст ответа.', reply_markup=onlyback_keyboard())
        elif data == 'back':
            step[user_id] = 6.1
            await callback.message.edit_reply_markup(None)
            await callback.message.answer('Шаг 6. Как ты хочешь добавить задачу?', reply_markup=files_keyboard())
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
    await message.answer('Шаг 1. Выбери авторов задачи из списка. Если не хочешь указывать, нажми "Пропустить".', reply_markup=tags_keyboard(tags_db, answers[user_id]['authors']))

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
    await message.answer('Шаг 3. Выбери олимпиаду, на которой встретилась задача, из списка. Этот шаг обязателен, так как ты указал год.', reply_markup=noskip_onetag_keyboard(tags_db, answers[user_id]['olympiad']))

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
    await message.answer('Шаг 4. Выбери из списка язык, которому посвящена задача. Если не хочешь указывать, нажми "Пропустить".', reply_markup=tags_keyboard(tags_db, answers[user_id]['language']))

async def get_tags5(message: Message, user_id: int):
    tags_db = dai_tags() #тэги из бд
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
    await message.answer('Шаг 5. Выбери тэги, связанные с задачей. Если не хочешь указывать, нажми "Пропустить".', reply_markup=tags_keyboard(tags_db, answers[user_id]['tags']))

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
                await message.answer('Пожалуйста, введи корректный год.')
        else:
            await message.answer('Пожалуйста, введи год числом.')
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

        await message.answer(f'Ты указал олимпиаду "{text.strip()}". Если это верно, нажми "Готово". Если ты хочешь указать другую, выбери ее из списка.')

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
            await message.answer('Шаг 7. Как ты хочешь добавить ответ на задачу?', reply_markup=files_keyboard())
        else:
            await message.answer('Пожалуйста, отправь файл с задачей.', reply_markup=onlyback_keyboard())
        return
    elif step[user_id] == 6.3:
        task_text = message.text.strip()
        if not task_text:
            await message.answer('Пожалуйста, введи текст задачи.', reply_markup=onlyback_keyboard())
            return
        answers[user_id]['task_text'] = task_text
        answers[user_id]['task_file_id'] = None
        step[user_id] = 7.1
        await message.answer('Шаг 7. Как ты хочешь добавить ответ на задачу?', reply_markup=files_keyboard())
        return
    elif step[user_id] == 7.2:
        if message.document is not None:
            answers[user_id]['answer_file_id'] = message.document.file_id
            answers[user_id]['answer_text'] = None
            await taskfile(message, user_id)
        else:
            await message.answer('Пожалуйста, отправь файл с ответом.', reply_markup=onlyback_keyboard())
        return
    elif step[user_id] == 7.3:
        answer_text = message.text.strip()
        if not answer_text:
            await message.answer('Пожалуйста, введи текст ответа.', reply_markup=onlyback_keyboard())
            return
        answers[user_id]['answer_text'] = answer_text
        answers[user_id]['answer_file_id'] = None
        await taskfile(message, user_id)
        return

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

    await message.answer('Спасибо! Твоя задача добавлена в базу данных.')

    admin_text = (
        f"Новая задача ожидает модерации!\n\n"
        f"Название: {title or 'Без названия'}\n"
        f"Прислал: {message.from_user.full_name} (@{message.from_user.username})"
    )
    for admin_id in adm:
        await bot.send_message(chat_id=admin_id, text=admin_text, parse_mode="HTML")
    if user_id in step:
        del step[user_id]
    if user_id in answers:
        del answers[user_id]

@start_router.message(Command('backup'))
async def backup(message: Message):
    user_id = message.from_user.id
    if user_id not in adm:
        await message.answer('У вас нет прав для этого действия.')
        return
    dbf = FSInputFile('olympiad_tasks.db')
    await message.answer_document(dbf, caption='Бэкап БД')
#запуск бота
async def main():
    dp.include_router(admin)
    dp.include_router(start_router)
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())