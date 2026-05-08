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

#def get_tags_keyboard():
    #tags = pg_db.get_tags() #получаем теги из базы данных (пока неясно как)
    #keyboard = InlineKeyboardMarkup(inline_keyboard=[
        #[InlineKeyboardButton(text=tag, callback_data=f"tag_{tag}")] for tag in tags
    #])
    #return keyboard

#начало
@start_router.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer('Привет! Это база лингвистических задач, в которой ты можешь найти задания по ключевым словам, автору, олимпиаде и т. п. Пиши /add, чтобы добавить задачу, или /search, чтобы найти задачу.')

@start_router.message(Command('add'))
async def cmd_add(message: Message):
    user_id = message.from_user.id
    step[user_id] = 1
    await message.answer('Шаг 1. Добавьте авторов задачи. Если не помните, нажмите "Пропустить".', parse_mode='Markdown', reply_markup=skip_keyboard())

#скипы каждого шага
@start_router.callback_query()
async def skip(callback: CallbackQuery):
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
            await callback.message.answer('Шаг 5. Выберите теги, связанные с задачей. Если не помните, нажмите "Пропустить".', parse_mode='Markdown', reply_markup=skip_keyboard())
        elif step[user_id] == 5:
            answers[user_id]['tags'] = None
            await callback.message.edit_reply_markup(None)
            await callback.message.answer('Спасибо! Ваша задача добавлена в базу данных.')

            all_data[user_id] = answers[user_id]
            save_data(all_data)
            del step[user_id]
            del answers[user_id]

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
        step[user_id] = 5
        await message.answer('Шаг 5. Выберите теги, связанные с задачей. Если нет подходящих, нажмите "Пропустить".', parse_mode='Markdown', reply_markup=skip_keyboard())
    elif step[user_id] == 5:
        answers[user_id]['tags'] = text.split(',').strip()
        await message.answer('Спасибо! Ваша задача добавлена в базу данных.')

        all_data[user_id] = answers[user_id]
        save_data(all_data)
        del step[user_id]
        del answers[user_id]

@start_router.message(Command('search'))
async def cmd_search(message: Message):
    await message.answer('Помните ли вы название задачи?')

async def main():
    #scheduler.add_job(send_time_msg, 'interval', seconds=10)
    #scheduler.start()
    dp.include_router(start_router)
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
