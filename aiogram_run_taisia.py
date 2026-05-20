# ========== ПОИСК ЗАДАЧ ==========

# Импортируем функцию поиска из db
from db import top_search
import asyncio
import uuid
import os

from create_bot import bot, dp
from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

start_router = Router()

# Словари для хранения состояния поиска
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
    buttons.append([InlineKeyboardButton(text="НАЧАТЬ ПОИСК", callback_data="start_search")])
    buttons.append([InlineKeyboardButton(text="ОТМЕНА", callback_data="cancel_search")])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def make_cancel_keyboard(): #Клавиатура для отмены поиска
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Отменить поиск", callback_data="cancel_search")]
    ])
    return keyboard

def results_keyboard(results, current_index): #Клавиатура для навигации по результатам поиска"
    buttons = []
    if current_index > 0:
        buttons.append(InlineKeyboardButton(text="⬅️ Назад", callback_data="prev_result"))
    if current_index < len(results) - 1:
        buttons.append(InlineKeyboardButton(text="Вперед ➡️", callback_data="next_result"))
    buttons.append(InlineKeyboardButton(text="Завершить поиск", callback_data="cancel_search"))
    return InlineKeyboardMarkup(inline_keyboard=[buttons])

@start_router.message(Command('search'))
async def cmd_search(message: Message):
    """Начало поиска: выбор параметров"""
    user_id = message.from_user.id
    
    search_step[user_id] = "choosing_params"
    search_params[user_id] = []
    
    await message.answer(
        "🔍 *ПОИСК ЗАДАЧИ*\n\n"
        "Выбери параметры, которые ты помнишь о задаче.\n"
        "Можно выбрать несколько. Нажми на параметр, чтобы добавить или убрать его.\n\n"
        "Когда выберешь всё, что помнишь, нажми «НАЧАТЬ ПОИСК».",
        parse_mode="Markdown",
        reply_markup=make_params_keyboard([])
    )

@start_router.callback_query()
async def handle_search_callbacks(callback: CallbackQuery):
    """Обрабатывает все callback-запросы от кнопок поиска"""
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
    
    # Выбор параметра
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
    
    # Начало поиска
    if data == "start_search":
        if not search_params[user_id]:
            await callback.answer("Выбери хотя бы один параметр!")
            return
        
        # Инициализируем сбор значений
        search_values[user_id] = {}
        search_index[user_id] = 0
        
        # Убираем клавиатуру выбора параметров
        await callback.message.edit_reply_markup(None)
        
        # Начинаем опрос параметров
        await ask_next_param(callback.message, user_id)
        await callback.answer()
        return

async def ask_next_param(message: Message, user_id: int): #Спрашивает пользователя о значении следующего параметра
    params_list = search_params[user_id]
    current_index = search_index[user_id]
    
    # Если все параметры уже опрошены — запускаем поиск
    if current_index >= len(params_list):
        await perform_search(message, user_id)
        return
    
    # Какой параметр сейчас спрашиваем
    current_param = params_list[current_index]
    
    # Словарь с понятными названиями параметров и пояснениями
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


@start_router.message()
async def handle_search_input(message: Message):
    """
    Обрабатывает текстовые ответы пользователя на вопросы о параметрах
    """
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
    
    # Важно: нужно создать словарь со ВСЕМИ параметрами (даже теми, что не выбраны)
    # Для невыбранных параметров значение = None
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






async def main():
    dp.include_router(start_router)
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())