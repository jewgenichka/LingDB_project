import asyncio

from create_bot import bot, dp
from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message
# from work_time.time_func import send_time_msg

start_router = Router()

@start_router.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer('Привет!')

async def main():
    #scheduler.add_job(send_time_msg, 'interval', seconds=10)
    #scheduler.start()
    dp.include_router(start_router)
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())