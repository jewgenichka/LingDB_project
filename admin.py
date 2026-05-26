from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

from create_bot import admins
from db import sptasks_na_odobrenie, odobrenie, udalenie, redaktor

class Edit(StatesGroup):
    column = State()
    value = State()

admin = Router()

pending = {}
index = {}
mdata = {}

adm = admins

async def is_admin(user_id: int) -> bool:
    return user_id in adm

async def pending_tasks(message: Message, user_id: int = None, task_id: int = 0):
    if user_id is None:
        user_id = message.from_user.id

    if not await is_admin(user_id):
        await message.answer("У вас нет прав для просмотра этого раздела.")
        return
    
    tasks = pending.get(user_id, [])
    if not tasks:
        await message.answer("Нет задач на одобрение.")
        return
    if task_id >= len(tasks):
        await message.answer('Задачи кончились :(')
        return
    task = tasks[task_id]
    index[user_id] = task_id

    text = f"Айди: {task['id']}\nЗадача: {task.get('title', 'Без названия')}\nАвтор(ы): {task.get('authors', '-')}\nТег(и): {task.get('tags', '-')}\nОлимпиада: {task.get('olympiad', '-')}\nГод: {task.get('year', '-')}\nЯзык(и): {task.get('language', '-')}"
    
    buttons = []
    buttons.append([InlineKeyboardButton(text="Одобрить", callback_data="dobro"), InlineKeyboardButton(text="Отклонить", callback_data="otklon")])
    buttons.append([InlineKeyboardButton(text="Редактировать", callback_data="edit")])
    row = []
    if task_id > 0:
        row.append(InlineKeyboardButton(text="Назад", callback_data='pred'))
    if task_id < len(tasks) - 1:
        row.append(InlineKeyboardButton(text='Вперед', callback_data='next'))
    if row:
        buttons.append(row)
    buttons.append([InlineKeyboardButton(text="Выйти", callback_data="exit")])
    await message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

async def edit(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    
    if not await is_admin(user_id):
        await callback.answer("Нет прав.")
        return
    
    now = index.get(user_id, 0)
    tasks = pending[user_id]
    
    if now >= len(tasks):
        await callback.answer("Ошибка: задача не найдена")
        return
    
    task_id = tasks[now]['id']
    await state.update_data(task_id=task_id)
    await state.set_state(Edit.column)

    columns = ["title", "authors", "tags", "olympiad", "year", "language"]
    buttons = []
    for i in columns:
        buttons.append([InlineKeyboardButton(text=i, callback_data=f"col_{i}")])
    buttons.append([InlineKeyboardButton(text="Назад", callback_data="cancel")])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    await callback.message.answer("Что вы хотите отредактировать?", reply_markup=keyboard)
    await callback.answer()

@admin.callback_query(F.data.startswith("col_"))
async def column(callback: CallbackQuery, state: FSMContext):
    column = callback.data.replace("col_", "")
    await state.update_data(column=column)
    await state.set_state(Edit.value)
    await callback.message.answer(f"Введите новое значение для поля *{column}*:", parse_mode="Markdown")
    await callback.answer()

@admin.callback_query(F.data == "cancel")
async def cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.delete()
    await callback.answer("Редактирование отменено")

@admin.message(Edit.value)
async def edit_value(message: Message, state: FSMContext):
    data = await state.get_data()
    task_id = data.get('task_id')
    column = data.get('column')
    new_value = message.text.strip()
    
    if not task_id or not column:
        await message.answer("Ошибка: нет данных для редактирования")
        await state.clear()
        return
    
    redaktor(task_id, column, new_value)
    
    await message.answer(f"✅ Поле *{column}* обновлено на: {new_value}", parse_mode="Markdown")
    
    from db import sptasks_na_odobrenie
    tasks = sptasks_na_odobrenie()
    user_id = message.from_user.id
    pending[user_id] = tasks
    
    # Показываем обновлённую задачу
    await state.clear()
    await pending_tasks(message, user_id, index.get(user_id, 0))
    
@admin.message(Command("pending"))
async def cmd_pending(message: Message):
    user_id = message.from_user.id
    if not await is_admin(user_id):
        await message.answer("У вас нет прав для просмотра этого раздела.")
        return
    tasks = sptasks_na_odobrenie()
    if not tasks:
        await message.answer("Нет задач на одобрение.")
        return
    pending[user_id] = tasks
    index[user_id] = 0
    await pending_tasks(message, user_id=user_id, task_id=0)

@admin.message(Command("moderate"))
async def moderate(message: Message):
    user_id = message.from_user.id
    if not await is_admin(user_id):
        await message.answer("У вас нет прав для просмотра этого раздела.")
        return
    from db import dai_all
    approved = [task for task in dai_all() if task.get('status') == 'approved']
    if not approved:
        await message.answer("Нет одобренных задач.")
        return
    mdata[user_id] = {'tasks': approved, 'index': 0}
    tasks = mdata[user_id]['tasks']
    page = mdata[user_id]['index']
    total = (len(tasks) + 9) // 10
    start = page * 10
    end = start + 10
    buttons = []
    for task in tasks[start:end]:
        buttons.append([InlineKeyboardButton(text=f"{task.get('title', 'Без названия')} (ID: {task['id']})", callback_data=f"mod_{task['id']}")])
    row = []
    if page > 0:
        row.append(InlineKeyboardButton(text="Назад", callback_data="mod_prev"))
    if page < total - 1:
        row.append(InlineKeyboardButton(text="Вперед", callback_data="mod_next"))
    if row:
        buttons.append(row)
    buttons.append([InlineKeyboardButton(text="Выйти", callback_data="mod_exit")])
    await message.answer(f"Одобренные задачи (страница {page + 1} из {total}):", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

@admin.callback_query(F.data.in_({"dobro", "otklon", "edit", "pred", "next", "exit"}) | F.data.startswith("mod_"))
async def callback(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    if not await is_admin(user_id):
        await callback.answer("У вас нет прав для выполнения этого действия.")
        return
    
    data = callback.data

    if data == "mod_exit":
        await callback.message.delete()
        await callback.answer("Вы вышли из режима просмотра одобренных задач.")
        return
    if data == "mod_prev":
        if user_id in mdata:
            mdata[user_id]['index'] = max(0, mdata[user_id]['index'] - 1)
            tasks = mdata[user_id]['tasks']
            page = mdata[user_id]['index']
            total = (len(tasks) + 9) // 10
            start = page * 10
            end = start + 10
            buttons = []
            for task in tasks[start:end]:
                buttons.append([InlineKeyboardButton(text=f"{task.get('title', 'Без названия')} (ID: {task['id']})", callback_data=f"mod_{task['id']}")])
            row = []
            if page > 0:
                row.append(InlineKeyboardButton(text="Назад", callback_data="mod_prev"))
            if page < total - 1:
                row.append(InlineKeyboardButton(text="Вперед", callback_data="mod_next"))
            if row:
                buttons.append(row)
            buttons.append([InlineKeyboardButton(text="Выйти", callback_data="mod_exit")])
            await callback.message.edit_text(f"Одобренные задачи (страница {page + 1} из {total}):", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
        await callback.answer()
        return
    if data == "mod_next":
        if user_id in mdata:
            mdata[user_id]['index'] = min(len(mdata[user_id]['tasks']) - 1, mdata[user_id]['index'] + 1)
            tasks = mdata[user_id]['tasks']
            page = mdata[user_id]['index']
            total = (len(tasks) + 9) // 10
            start = page * 10
            end = start + 10
            buttons = []
            for task in tasks[start:end]:
                buttons.append([InlineKeyboardButton(text=f"{task.get('title', 'Без названия')} (ID: {task['id']})", callback_data=f"mod_{task['id']}")])
            row = []
            if page > 0:
                row.append(InlineKeyboardButton(text="Назад", callback_data="mod_prev"))
            if page < total - 1:
                row.append(InlineKeyboardButton(text="Вперед", callback_data="mod_next"))
            if row:
                buttons.append(row)
            buttons.append([InlineKeyboardButton(text="Выйти", callback_data="mod_exit")])
            await callback.message.edit_text(f"Одобренные задачи (страница {page + 1} из {total}):", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
        await callback.answer()
        return
    if data.startswith("mod_"):
        task_id = int(data.split("_")[1])
        from db import change_status
        change_status(task_id)
        await callback.answer("Статус задачи изменён.")
        from db import dai_all
        approved = [task for task in dai_all() if task.get('status') == 'approved']
        if approved:
            mdata[user_id] = {'tasks': approved, 'index': 0}
            tasks = approved
            page = 0
            total = (len(tasks) + 9) // 10
            start = page * 10
            end = start + 10
            buttons = []
            for task in tasks[start:end]:
                buttons.append([InlineKeyboardButton(text=f"{task.get('title', 'Без названия')} (ID: {task['id']})", callback_data=f"mod_{task['id']}")])
            row = []
            if page > 0:
                row.append(InlineKeyboardButton(text="Назад", callback_data="mod_prev"))
            if page < total - 1:
                row.append(InlineKeyboardButton(text="Вперед", callback_data="mod_next"))
            if row:
                buttons.append(row)
            buttons.append([InlineKeyboardButton(text="Выйти", callback_data="mod_exit")])
            await callback.message.edit_text(f"Одобренные задачи (страница {page + 1} из {total}):", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
        else:
            await callback.message.delete()
            await callback.answer("Нет одобренных задач.")
        return
    


    if data == "exit":
        user_id = callback.from_user.id
        if user_id in pending:
            del pending[user_id]
        if user_id in index:
            del index[user_id]
        await callback.message.delete()
        await callback.answer("Вы вышли из режима админа")
        return

    task_id = pending[user_id][index[user_id]]['id']
    if data == "dobro":
        sender = odobrenie(task_id)
        await callback.answer("Задача одобрена.")
        if sender:
            try:
                await callback.bot.send_message(sender, f"Ваша задача (ID: {task_id}) была одобрена и добавлена в базу данных.")
            except Exception as e:
                print(f"Ошибка при отправке сообщения пользователю {sender}: {e}")
        return
    elif data == "otklon":
        sender = udalenie(task_id)
        await callback.answer("Задача отклонена.")
        if sender:
            try:
                await callback.bot.send_message(sender, f"Ваша задача (ID: {task_id}) была отклонена.")
            except Exception as e:
                print(f"Ошибка при отправке сообщения пользователю {sender}: {e}")
        return
    elif data == "edit":
        await edit(callback, state)
        await callback.answer("Задача на редактировании.")
        return
    elif data == "pred":
        user_id = callback.from_user.id
        if not await is_admin(user_id):
            await callback.answer("У вас нет прав для выполнения этого действия.")
            return
        now = index.get(user_id, 0)
        await callback.message.delete()
        await pending_tasks(callback.message, user_id, now - 1)
        await callback.answer()
        return
    elif data == "next":
        user_id = callback.from_user.id
        if not await is_admin(user_id):
            await callback.answer("У вас нет прав для выполнения этого действия.")
            return
        now = index.get(user_id, 0)
        await callback.message.delete()
        await pending_tasks(callback.message, user_id, now + 1)
        await callback.answer()
        return

    tasks = sptasks_na_odobrenie()
    pending[user_id] = tasks
    if index[user_id] >= len(tasks):
        await callback.message.answer("Нет больше задач на одобрение.")
        return
    await pending_tasks(callback.message, user_id=user_id, task_id=index[user_id])