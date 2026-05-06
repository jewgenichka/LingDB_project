import asyncio

from create_bot import bot, dp
from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
# from work_time.time_func import send_time_msg

start_router = Router()

@start_router.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer('Привет! Это база лингвистических задач, в которой ты можешь найти задания по ключевым словам, автору, олимпиаде и т. п. Ты хотел бы найти или добавить задачу?')

def get_author_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Да", callback_data="author_yes")],
        [InlineKeyboardButton(text="Нет", callback_data="author_no")]
    ])
    return keyboard

@start_router.message(Command('add'))
async def cmd_add(message: Message):
    await message.answer('Добавить авторов задачи?', reply_markup=get_author_keyboard())

@start_router.callback_query(lambda c: c.data in ['author_yes', 'author_no'])
async def process_author_choice(callback: CallbackQuery):
    if callback.data == 'author_yes':
        await callback.message.edit_text("Введите авторов задачи (можно несколько через запятую):")
        await callback.answer()

@start_router.message(Command('search'))
async def cmd_search(message: Message):
    await message.answer('Поиск задачи')

async def main():
    #scheduler.add_job(send_time_msg, 'interval', seconds=10)
    #scheduler.start()
    dp.include_router(start_router)
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())