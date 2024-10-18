import os
import logging
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv
from db import add_manager, create_connection, create_table, save_vacation_request, get_vacation_request, delete_vacation_request, save_vacation
from aiogram.filters import Command
from datetime import datetime, timedelta
from notify import daily_job

# Загрузка токена и админов из .env
load_dotenv()
API_TOKEN = os.getenv("TELEGRAM_TOKEN")
ADMIN_USERNAMES = os.getenv("ADMIN_USERNAMES").split(',')

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Инициализация бота и диспетчера
bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Подключение к базе данных
db_conn = create_connection()

# Создание таблиц
create_table(db_conn)

# Функция для отправки уведомлений
async def send_notification(chat_id, message):
    await bot.send_message(chat_id, message)

# Планирование уведомлений
async def schedule_vacation_notifications(chat_id, start_date_str, end_date_str):
    # Преобразование строковых дат в объекты datetime
    start_date = datetime.strptime(start_date_str, "%d/%m/%Y")
    end_date = datetime.strptime(end_date_str, "%d/%m/%Y")
    
    # Текущая дата и время
    now = datetime.now()

    # Уведомления за 10, 5, 2 и 0 дней до начала отпуска
    notification_days_before_start = [10, 5, 2, 0]
    for days in notification_days_before_start:
        notification_time = start_date - timedelta(days=days)
        delay = (notification_time - now).total_seconds()
        if delay > 0:
            await asyncio.sleep(delay)
            await send_notification(chat_id, f"До начала отпуска осталось {days} дней.")

    # Уведомления за 3 и 0 дней до окончания отпуска
    notification_days_before_end = [3, 0]
    for days in notification_days_before_end:
        notification_time = end_date - timedelta(days=days)
        delay = (notification_time - now).total_seconds()
        if delay > 0:
            await asyncio.sleep(delay)
            await send_notification(chat_id, f"До конца отпуска осталось {days} дней.")
    
    # Сообщение в день окончания отпуска
    if (end_date - now).total_seconds() > 0:
        await send_notification(chat_id, "Отпуск завершен сегодня.")

# Проверка на менеджера
def is_manager(username):
    cursor = db_conn.cursor()
    cursor.execute("SELECT 1 FROM managers WHERE manager_username = ?", (username,))
    return cursor.fetchone() is not None

# Команда /cancel_vacation (только для менеджеров)
@dp.message(Command("cancel_vacation"))
async def cancel_vacation(message: types.Message):
    chat_id = message.chat.id

    # Проверка прав менеджера
    if not is_manager(message.from_user.username):
        await message.reply("У вас нет прав для отмены отпуска.")
        return

    # Проверка, есть ли активный отпуск
    cursor = db_conn.cursor()
    cursor.execute("SELECT * FROM vacations WHERE chat_id = ?", (chat_id,))
    vacation = cursor.fetchone()

    if not vacation:
        await message.reply("Нет активных отпусков для отмены.")
        return

    # Удаление отпуска
    cursor.execute("DELETE FROM vacations WHERE chat_id = ?", (chat_id,))
    db_conn.commit()

    await message.reply("Отпуск был отменен.")

# Команда /change_vacation (только для менеджеров)
@dp.message(Command("change_vacation"))
async def change_vacation(message: types.Message):
    chat_id = message.chat.id

    # Проверка прав менеджера
    if not is_manager(message.from_user.username):
        await message.reply("У вас нет прав для изменения отпуска.")
        return

    args = message.text.split()
    if len(args) != 2:
        await message.reply("Использование: /change_vacation DD/MM/YYYY-DD/MM/YYYY")
        return

    start_date, end_date = args[1].split('-')

    # Проверка, есть ли активный отпуск
    cursor = db_conn.cursor()
    cursor.execute("SELECT * FROM vacations WHERE chat_id = ?", (chat_id,))
    vacation = cursor.fetchone()

    if not vacation:
        await message.reply("Нет активных отпусков для изменения.")
        return

    # Изменение дат отпуска
    cursor.execute("UPDATE vacations SET start_date = ?, end_date = ? WHERE chat_id = ?", (start_date, end_date, chat_id))
    db_conn.commit()

    await message.reply(f"Даты отпуска изменены на {start_date} - {end_date}.")

# Команда /vacation с проверкой на существующий отпуск
@dp.message(Command("vacation"))
async def vacation_request(message: types.Message):
    chat_id = message.chat.id
    developer_username = message.from_user.username
    args = message.text.split()

    if len(args) != 2:
        await message.reply("Использование: /vacation DD/MM/YYYY-DD/MM/YYYY")
        return

    start_date, end_date = args[1].split('-')

    # Проверка, есть ли уже отпуск в этом чате
    cursor = db_conn.cursor()
    cursor.execute("SELECT * FROM vacations WHERE chat_id = ?", (chat_id,))
    existing_vacation = cursor.fetchone()

    if existing_vacation:
        await message.reply("Уже существует активный отпуск для этого чата.")
        return

    # Сохранение запроса на отпуск
    save_vacation_request(db_conn, chat_id, developer_username, start_date, end_date)

    # Получение всех администраторов чата
    chat_admins = await bot.get_chat_administrators(chat_id)
    admin_usernames = [admin.user.username for admin in chat_admins]

    # Отправка запроса только тем менеджерам, которые есть в чате
    cursor.execute("SELECT manager_username FROM managers")
    all_managers = cursor.fetchall()
    managers_in_chat = [f"@{manager[0]}" for manager in all_managers if manager[0] in admin_usernames]

    if managers_in_chat:
        manager_tags = ', '.join(managers_in_chat)
        await message.reply(f"{manager_tags}, можно ли сотруднику @{developer_username} взять отпуск с {start_date} по {end_date}?")
    else:
        await message.reply("Нет доступных менеджеров в этом чате.")

# Команда /approve
@dp.message(Command("approve"))
async def approve_vacation(message: types.Message):
    chat_id = message.chat.id

    # Получение данных запроса на отпуск
    request = get_vacation_request(db_conn, chat_id)
    if not request:
        await message.reply("Нет активных запросов на отпуск для этого чата.")
        return

    developer_username, start_date, end_date = request

    # Сохранение одобренного отпуска
    save_vacation(db_conn, chat_id, start_date, end_date)

    # Удаление временного запроса
    delete_vacation_request(db_conn, chat_id)

    await message.reply(f"Отпуск для @{developer_username} с {start_date} по {end_date} одобрен!")

    # Запуск уведомлений
    asyncio.create_task(schedule_vacation_notifications(chat_id, start_date, end_date))

# Команда /disapprove
@dp.message(Command("disapprove"))
async def disapprove_vacation(message: types.Message):
    chat_id = message.chat.id

    # Получение данных запроса на отпуск
    request = get_vacation_request(db_conn, chat_id)
    if not request:
        await message.reply("Нет активных запросов на отпуск для этого чата.")
        return

    developer_username = request[0]

    # Удаление временного запроса
    delete_vacation_request(db_conn, chat_id)

    await message.reply(f"Запрос на отпуск для @{developer_username} отклонен.")
    
# Команда /add_manager (доступно только админам)
@dp.message(Command("add_manager"))
async def cmd_add_manager(message: types.Message):
    if message.from_user.username not in ADMIN_USERNAMES:
        await message.reply("У вас нет прав для добавления менеджеров.")
        return

    args = message.text.split()
    if len(args) != 2:
        await message.reply("Использование: /add_manager @username")
        return

    manager_username = args[1].replace('@', '')

    # Добавляем менеджера в базу данных
    add_manager(db_conn, manager_username)

    await message.reply(f"Менеджер @{manager_username} добавлен.")

# Запуск бота
async def main():
    create_table(db_conn)
    asyncio.create_task(daily_job(bot, db_conn))
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
