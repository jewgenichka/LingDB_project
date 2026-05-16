#пока что здесь хранится все, связанное с перепиской с пользователем, но в будущем это будет разделено на несколько файлов
import asyncio
import json
import os

from create_bot import bot, dp
from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

file = 'tasks.json'

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
        buttons.append(InlineKeyboardButton(text=chosen, callback_data=f"tag_{tag}"))
    
    lower_row = []
    if chosen_tags:
        lower_row.append(InlineKeyboardButton(text="Готово", callback_data="done"))
    lower_row.append(InlineKeyboardButton(text="Пропустить", callback_data="skip"))
    lower_row.append(InlineKeyboardButton(text="Нет в списке", callback_data="custom_tag"))
    return InlineKeyboardMarkup(inline_keyboard=[buttons, lower_row])

#начало
@start_router.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer('Привет! Это база лингвистических задач, в которой ты можешь найти задания по ключевым словам, автору, олимпиаде и т. п. Пиши /add, чтобы добавить задачу, или /search, чтобы найти задачу.')

@start_router.message(Command('add'))
async def cmd_add(message: Message):
    user_id = message.from_user.id
    step[user_id] = 1
    await message.answer('Шаг 1. Добавьте авторов задачи. Если не помните, нажмите "Пропустить".', parse_mode='Markdown', reply_markup=skip_keyboard())

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
            await callback.message.answer('Шаг 3. Добавьте олимпиаду, на которой встретилась задача. Если не помните, нажмите "Пропустить".', parse_mode='Markdown', reply_markup=skip_keyboard())
        elif step[user_id] == 3:
            answers[user_id]['olympiad'] = None
            await callback.message.edit_reply_markup(None)
            step[user_id] = 4
            await callback.message.answer('Шаг 4. Добавьте язык, которому посвящена задача. Если не помните, нажмите "Пропустить".', parse_mode='Markdown', reply_markup=skip_keyboard())
        elif step[user_id] == 4:
            answers[user_id]['language'] = None
            await callback.message.edit_reply_markup(None)
            step[user_id] = 5
            await get_tags(callback.message, user_id) 
        elif step[user_id] == 5.1:
            answers[user_id]['tags'] = None
            await callback.message.edit_reply_markup(None)
            await task_save(callback.message, user_id)
            await callback.answer('Вы пропустили выбор тегов.')
            return
    
        await callback.answer()
        return

    elif step.get(user_id) == 5.1:
        tags_db = ['морфология', 'лексика', 'фонетика', 'синтаксис', 'озарение', 'история языка'] #Здесь затем будет функция доставания тегов из базы данных        
        
        if data.startswith("tag_"):
            tag = data[4:]

            if tag in answers[user_id]['chosen_tags']:
                answers[user_id]['chosen_tags'].remove(tag)
                await callback.answer(f'Тег "{tag}" удалён.')
            else:
                answers[user_id]['chosen_tags'].append(tag)
                await callback.answer(f'Тег "{tag}" добавлен.')
            await callback.message.edit_reply_markup(reply_markup=tags_keyboard(['морфология', 'лексика', 'фонетика', 'синтаксис', 'озарение', 'история языка'], answers[user_id]['chosen_tags']))
    
        elif data == "custom_tag":
            step[user_id] = 5.2
            await callback.message.answer('Пожалуйста, введите свои теги через запятую.')
            await callback.answer()
    
        elif data == "done":
            answers[user_id]['tags'] = answers[user_id]['chosen_tags']
            await callback.message.edit_reply_markup(None)
            await task_save(callback.message, user_id)
            await callback.answer('Выбор тегов завершён.')
    
        elif data == "skip":
            answers[user_id]['tags'] = None
            await callback.message.edit_reply_markup(None)
            await task_save(callback.message, user_id)
            await callback.answer('Вы пропустили выбор тегов.')

async def step2(message: Message, user_id: int):
    if step[user_id] == 2:
        await message.answer('Шаг 2. Добавьте год олимпиады. Если не помните, нажмите "Пропустить".', parse_mode='Markdown', reply_markup=skip_keyboard())
async def step3(message: Message, user_id: int):
    if step[user_id] == 3:
        await message.answer('Шаг 3. Добавьте олимпиаду, на которой встретилась задача. Если не помните, нажмите "Пропустить".', parse_mode='Markdown', reply_markup=skip_keyboard())

async def step4(message: Message, user_id: int):
    if step[user_id] == 4:
        await message.answer('Шаг 4. Добавьте язык, которому посвящена задача. Если не помните, нажмите "Пропустить".', parse_mode='Markdown', reply_markup=skip_keyboard())

async def step5(message: Message, user_id: int):
    if step[user_id] == 5:
        await message.answer('Шаг 5. Выберите теги, связанные с задачей. Если не помните, нажмите "Пропустить".', parse_mode='Markdown', reply_markup=skip_keyboard())

async def get_tags(message: Message, user_id: int):
    tags_db = ['морфология', 'лексика', 'фонетика', 'синтаксис', 'озарение', 'история языка'] #Здесь затем будет функция доставания тегов из базы данных

    if user_id not in answers:
        answers[user_id] = {}
    if 'chosen_tags' not in answers[user_id]:
        answers[user_id]['chosen_tags'] = []
    
    step[user_id] = 5.1
    await message.answer('Шаг 5. Выберите теги, связанные с задачей. Если нет подходящих, нажмите "Пропустить".', reply_markup=tags_keyboard(tags_db, answers[user_id]['chosen_tags']))

@start_router.message()
async def answer_message(message: Message):
    user_id = message.from_user.id

    if user_id not in step:
        return  # Если пользователь не начал процесс добавления, игнорируем сообщение

    text = message.text

    if step[user_id] == 1:
        answers[user_id] = {"authors": text}
        step[user_id] = 2
        await message.answer('Шаг 2. Добавьте год олимпиады. Если не помните, нажмите "Пропустить".', parse_mode='Markdown', reply_markup=skip_keyboard())
    elif step[user_id] == 2:
        if text.isdigit():
            year = int(text)            
            if 1900 <= year <= 2050:  
                answers[user_id]['year'] = year
                step[user_id] = 3
                await message.answer('Шаг 3. Добавьте олимпиаду, на которой встретилась задача. Если не помните, нажмите "Пропустить".', reply_markup=skip_keyboard())
            else:
                await message.answer('Пожалуйста, введите корректный год.')
        else:
            await message.answer('Пожалуйста, введите год числом.')
    elif step[user_id] == 3:
        answers[user_id]['olympiad'] = text
        step[user_id] = 4
        await message.answer('Шаг 4. Добавьте язык, которому посвящена задача. Если не помните, нажмите "Пропустить".', parse_mode='Markdown', reply_markup=skip_keyboard())
    elif step[user_id] == 4:
        answers[user_id]['language'] = text
        await get_tags(message, user_id)
    elif step[user_id] == 5.2:
        answers[user_id]['tags'] = [tag.strip() for tag in text.split(',')]
        await task_save(message, user_id)

async def task_save(message: Message, user_id: int):
    if user_id not in all_data:
        all_data[user_id] = []
    all_data[user_id].append(answers[user_id])
    save_data(all_data)

    await message.answer('Спасибо! Ваша задача добавлена в базу данных.')
    del step[user_id]
    del answers[user_id]

@start_router.message(Command('search'))
async def cmd_search(message: Message):
    await message.answer('Помните ли вы название задачи?')

async def main():
    dp.include_router(start_router)
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
