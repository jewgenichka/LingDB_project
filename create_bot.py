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

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(BASE_DIR, '.env')

class EnvConfig:
    def __getitem__(self, key):
        return os.environ[key]
    def get(self, key, default=None):
        return os.environ.get(key, default)
    def __call__(self, key):
        return os.environ[key]
        
if os.path.exists('.env'):
    config = Config(repository=RepositoryEnv(env_path))
else:
    config = EnvConfig()
TOKEN = config('TOKEN')
ADMINS = config('ADMINS')
admins = [int(admin_id) for admin_id in ADMINS.split(',')]

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())