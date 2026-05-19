#у меня чет не работало с файлом .env поэтому здесь прописаны токен и админы

#айди отправителя, название, текст, айди файл, текст ответ, айди ответа, авторы (несколько), теги (несколько), олимпиада, (если есть олимпиада, то сохраняется) год олимпиады, язык(и)

import logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from decouple import Config, RepositoryEnv
import os

#pg_db = PostgresHandler(config('PG_LINK'))

ADMINS="1365235944"
admins = [int(admin_id) for admin_id in ADMINS.split(',')]

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

TOKEN='8745809932:AAEz04VzrQdOd3CH2VyGCw75nN-fAIxGJhI'
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())