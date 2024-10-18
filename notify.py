import asyncio
from datetime import datetime, timedelta


# Функция для отправки уведомлений
async def send_notification(bot, chat_id, message):
    await bot.send_message(chat_id, message)

# Функция для проверки отпусков и удаления завершенных
async def check_vacations_and_notify(bot, db_conn):
    now = datetime.now()

    # Получение всех отпусков
    cursor = db_conn.cursor()
    cursor.execute("SELECT chat_id, start_date, end_date FROM vacations")
    vacations = cursor.fetchall()

    for vacation in vacations:
        chat_id, start_date_str, end_date_str = vacation
        start_date = datetime.strptime(start_date_str, "%d/%m/%Y")
        end_date = datetime.strptime(end_date_str, "%d/%m/%Y")

        # Проверяем сколько дней осталось до начала отпуска
        days_until_start = (start_date - now).days
        if days_until_start in [10, 7, 5, 2, 0]:
            await send_notification(bot, chat_id, f"До начала отпуска осталось {days_until_start} дней.")

        # Проверяем сколько дней осталось до конца отпуска
        days_until_end = (end_date - now).days
        if days_until_end in [10, 7, 5, 2, 0]:
            await send_notification(bot, chat_id, f"До конца отпуска осталось {days_until_end} дней.")

        # Если отпуск закончился, удаляем его
        if days_until_end < 0:
            cursor.execute("DELETE FROM vacations WHERE chat_id = ? AND start_date = ? AND end_date = ?", 
                           (chat_id, start_date_str, end_date_str))
            db_conn.commit()
            await send_notification(bot, chat_id, "Ваш отпуск завершился, запись удалена.")

async def daily_job(bot, db_conn):
    while True:
        await check_vacations_and_notify(bot, db_conn)
        # Задержка на 24 часа
        await asyncio.sleep(86400)