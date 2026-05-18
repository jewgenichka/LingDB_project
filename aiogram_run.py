#пока что здесь хранится все, связанное с перепиской с пользователем, но в будущем это будет разделено на несколько файлов

#поиск: название авторов теги олимпиада год языки. вывод топ-5 подходящих задач

import asyncio
import json
import uuid
import os

from create_bot import bot, dp
from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

file = 'tasks.json'
dir = 'tasks'
if not os.path.exists(dir):
    os.makedirs(dir)

def load_data():
    if os.path.exists(file):
        with open(file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}
def save_data(data):
    with open(file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
all_data = load_data()

step = {}
answers = {}

start_router = Router()

#кнопка скипа
def skip_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Пропустить", callback_data="skip")]
    ])
    return keyboard

def tags_keyboard(tags_db, chosen_tags):
    buttons = []

    for tag in tags_db:
        chosen = f"✅{tag}" if tag in chosen_tags else tag
        buttons.append([InlineKeyboardButton(text=chosen, callback_data=f"tag_{tag}")])
    
    lower_row = [InlineKeyboardButton(text="Готово", callback_data="done"), InlineKeyboardButton(text="Пропустить", callback_data="skip"), InlineKeyboardButton(text="Нет в списке", callback_data="custom_tag")]
    buttons.append(lower_row)
    return InlineKeyboardMarkup(inline_keyboard=buttons)

async def handle_tags(callback: CallbackQuery, user_id: int):
    data = callback.data
    info = answers[user_id].get('info')
    custom = answers[user_id].get('custom')
    next = answers[user_id].get('next')
    tags_db = answers[user_id].get('tags_db')
    
    if not info:
        return
    if data.startswith('tag_'):
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
        await callback.message.answer(f'Введите свои варианты для "{info}" через запятую.')
        await callback.answer()

    elif data == "done":
        all = list(set(answers[user_id].get(custom, []) + answers[user_id].get(info, [])))
        answers[user_id][info] = all

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
            await callback.message.answer('Шаг 2. Добавьте год олимпиады. Если не помните, нажмите "Пропустить".', reply_markup=skip_keyboard())
        elif next == 4:
            await get_tags4(callback.message, user_id)
        elif next == 5:
            await get_tags5(callback.message, user_id)
        elif next == 6:
            await callback.message.answer('Шаг 6. Загрузите файл с задачей или введите ее текстом.')
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
            await callback.message.answer('Шаг 2. Добавьте год олимпиады. Если не помните, нажмите "Пропустить".', reply_markup=skip_keyboard())
        elif next == 4:
            await get_tags4(callback.message, user_id)
        elif next == 5:
            await get_tags5(callback.message, user_id)
        elif next == 6:
            await callback.message.answer('Шаг 6. Загрузите файл с задачей или введите ее текстом.')
        await callback.answer()

#начало
@start_router.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer('Привет! Это база лингвистических задач, в которой ты можешь найти задания по ключевым словам, автору, олимпиаде и т. п. Пиши /add, чтобы добавить задачу, или /search, чтобы найти задачу.')

@start_router.message(Command('add'))
async def cmd_add(message: Message):
    user_id = message.from_user.id
    step[user_id] = 1
    await get_tags1(message, user_id)

#все коллбеки
@start_router.callback_query()
async def callbacks(callback: CallbackQuery):
    user_id = callback.from_user.id
    data = callback.data

    if data == "skip":
        if user_id not in answers:
            answers[user_id] = {}
        if step[user_id] == 1:
            answers[user_id]['authors'] = None
            await callback.message.edit_reply_markup(None)
            step[user_id] = 2
            await callback.message.answer('Шаг 2. Добавьте год олимпиады. Если не помните, нажмите "Пропустить".', parse_mode='Markdown', reply_markup=skip_keyboard())
        elif step[user_id] == 2:
            answers[user_id]['year'] = None
            await callback.message.edit_reply_markup(None)
            step[user_id] = 3
            await get_tags3(callback.message, user_id)
        elif step[user_id] == 3:
            answers[user_id]['olympiad'] = None
            await callback.message.edit_reply_markup(None)
            step[user_id] = 4
            await get_tags4(callback.message, user_id)
        elif step[user_id] == 4:
            answers[user_id]['language'] = None
            await callback.message.edit_reply_markup(None)
            step[user_id] = 5
            await get_tags5(callback.message, user_id) 

        elif step[user_id] == 1.1:
            answers[user_id]['authors'] == []
            await callback.message.edit_reply_markup(None)
            if 'custom_authors' in answers[user_id]:
                del answers[user_id]['custom_authors']
            await callback.answer()
            step[user_id] = 2
            await callback.message.answer('Шаг 2. Добавьте год олимпиады. Если не помните, нажмите "Пропустить".', parse_mode='Markdown', reply_markup=skip_keyboard())
            return
        elif step[user_id] == 3.1:
            answers[user_id]['olympiad'] = None
            await callback.message.edit_reply_markup(None)
            if 'custom_olympiad' in answers[user_id]:
                del answers[user_id]['custom_olympiad']
            await callback.answer()
            step[user_id] = 4
            await get_tags4(callback.message, user_id)
            return
        elif step[user_id] == 4.1:
            answers[user_id]['language'] = None
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
            step[user_id] = 6
            await callback.message.answer('Шаг 6. Отправьте файл с задачей.')
            return

    elif step.get(user_id) == 1.1:
        await handle_tags(callback, user_id)
    elif step.get(user_id) == 3.1:
        await handle_tags(callback, user_id)
    elif step.get(user_id) == 4.1:
        await handle_tags(callback, user_id)
    elif step.get(user_id) == 5.1:
        await handle_tags(callback, user_id)
    await callback.answer()
    return

async def get_tags1(message: Message, user_id: int):
    tags_db = ['Иткин И. Б.', 'Влахов А. В.', 'Бурлак С. А.'] #авторы из бд
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
    tags_db = ['ВСОШ', 'Высшая проба', 'КФУ', 'МОШ по лингвистике', 'Изумруд'] #олимпиады из бд
    if user_id not in answers:
        answers[user_id] = {}
    if 'olympiad' not in answers[user_id]:
        answers[user_id]['olympiad'] = []
    if 'custom_olympiad' not in answers[user_id]:
        answers[user_id]['custom_olympiad'] = []
    
    answers[user_id]['tags_db'] = tags_db
    answers[user_id]['info'] = 'olympiad'
    answers[user_id]['custom'] = 'custom_olympiad'
    answers[user_id]['next'] = 4

    step[user_id] = 3.1
    await message.answer('Шаг 3. Выберите олимпиаду, на которой встретилась задача, из списка. Если не хотите указывать, нажмите "Пропустить".', reply_markup=tags_keyboard(tags_db, answers[user_id]['olympiad']))

async def get_tags4(message: Message, user_id: int):
    tags_db = ['русский язык', 'китайский язык', 'древнерусский язык', 'эсперанто', 'токипона'] #языки из бд
    if user_id not in answers:
        answers[user_id] = {}
    if 'language' not in answers[user_id]:
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
    tags_db = ['морфология', 'лексика', 'фонетика', 'синтаксис', 'озарение', 'история языка'] #Здесь затем будет функция доставания тегов из базы данных

    if user_id not in answers:
        answers[user_id] = {}
    if 'tags' not in answers[user_id]:
        answers[user_id]['tags'] = []
    if 'customs' not in answers[user_id]:
        answers[user_id]['customs'] = []
    
    answers[user_id]['tags_db'] = tags_db
    answers[user_id]['info'] = 'tags'
    answers[user_id]['custom'] = 'customs'
    answers[user_id]['next'] = 6

    step[user_id] = 5.1
    await message.answer('Шаг 5. Выберите теги, связанные с задачей. Если не хотите указывать, нажмите "Пропустить".', reply_markup=tags_keyboard(tags_db, answers[user_id]['tags']))

@start_router.message()
async def answer_message(message: Message):
    user_id = message.from_user.id

    if user_id not in step:
        return  # Если пользователь не начал процесс добавления, игнорируем сообщение

    text = message.text

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
        answers[user_id]['custom_olympiad'] = [tag.strip() for tag in text.split(',')]

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
    elif step[user_id] == 6:
        if message.document is not None:
            await taskfile(message, user_id)
        else:
            await message.answer('Пожалуйста, отправьте файл с задачей.')
        return

#задача может быть введена с клавы (строка). ограничение по символам какое-то (пять строк?). (это еще будет написано)

async def taskfile(message: Message, user_id: int):
    if message.document is not None:
        info = await bot.get_file(message.document.file_id)
        downloaded = await bot.download_file(info.file_path)

        name = message.document.file_name
        save_path = os.path.join(dir, name)
        with open(save_path, 'wb') as f:
            f.write(downloaded.getvalue())

        task_id = str(uuid.uuid4()) #берем айдишник задачи, который будет использоваться для ее идентификации в базе данных
        task_data = answers[user_id]
        task_data['id'] = task_id

        if str(user_id) not in all_data: #процесс сохранения данных в бд
            all_data[str(user_id)] = []
        all_data[str(user_id)].append(task_data)
        save_data(all_data)
        await message.answer('Спасибо! Ваша задача добавлена в базу данных.')
        del step[user_id]
        del answers[user_id]
    else:
        await message.answer('Пожалуйста, отправьте файл с задачей.')

@start_router.message(Command('search'))
async def cmd_search(message: Message):
    await message.answer('Помните ли вы название задачи?')

#здесь будет логика поиска задач по базе данных

async def main():
    dp.include_router(start_router)
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())