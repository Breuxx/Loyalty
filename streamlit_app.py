import asyncio
import re
import sys
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError
import pandas as pd
from datetime import datetime, timedelta

# ============================
# Конфигурация: вставьте свои данные
# ============================
api_id = 12345678                     # Ваш API ID (целое число)
api_hash = 'your_api_hash_here'       # Ваш API hash (строка)
session_name = 'my_session'           # Имя файла сессии

# Хештег для поиска (измените при необходимости)
SEARCH_HASHTAG = "#A910"

# ============================
# Функция авторизации
# ============================
async def authorize(client: TelegramClient):
    await client.connect()
    if not await client.is_user_authorized():
        phone = input("Введите номер телефона (с международным кодом, например, +1234567890): ").strip()
        try:
            await client.send_code_request(phone)
        except Exception as e:
            print("Ошибка при отправке кода:", e)
            sys.exit(1)
        code = input("Введите код подтверждения, который вы получили: ").strip()
        try:
            await client.sign_in(phone, code=code)
        except SessionPasswordNeededError:
            password = input("Введите ваш пароль двухфакторной аутентификации: ").strip()
            await client.sign_in(password=password)
    print("Авторизация успешна!")

# ============================
# Функция получения сообщений из всех диалогов с фильтрацией по дате
# ============================
async def fetch_all_messages(client: TelegramClient, hashtag: str, limit_per_dialog: int = 1000, min_date=None):
    results = []
    dialogs = await client.get_dialogs()
    print(f"Найдено {len(dialogs)} чатов.")
    for dialog in dialogs:
        print(f"Обработка чата: {dialog.name} (ID: {dialog.id})")
        try:
            messages = await client.get_messages(dialog.entity, limit=limit_per_dialog)
        except Exception as e:
            print(f"Ошибка получения сообщений для {dialog.name}: {e}")
            continue
        # Если задана дата, фильтруем сообщения вручную
        if min_date is not None:
            messages = [msg for msg in messages if msg.date >= min_date]
        for msg in messages:
            if msg.text and hashtag in msg.text:
                results.append({
                    "chat_name": dialog.name,
                    "chat_id": dialog.id,
                    "date": msg.date,
                    "text": msg.text
                })
    return results

# ============================
# Функция формирования отчёта и сохранения в Excel
# ============================
def save_report(data, output_file: str):
    df = pd.DataFrame(data)
    if df.empty:
        print("Сообщения не найдены.")
        return False
    df['date'] = pd.to_datetime(df['date'])
    df['date_str'] = df['date'].dt.strftime("%Y-%m-%d %H:%M:%S")
    df['day'] = df['date'].dt.date
    df['week'] = df['date'].dt.strftime("%Y-%U")
    df['month'] = df['date'].dt.strftime("%Y-%m")
    df['year'] = df['date'].dt.strftime("%Y")
    try:
        df.to_excel(output_file, index=False)
        print(f"Excel файл успешно сохранён как '{output_file}'.")
        return True
    except Exception as e:
        print("Ошибка сохранения Excel файла:", e)
        return False

# ============================
# Основная функция
# ============================
async def main():
    client = TelegramClient(session_name, api_id, api_hash)
    await authorize(client)
    
    # Спрашиваем, анализировать ли только последние 7 дней
    choice = input("Анализировать только последние 7 дней? (Y/n): ").strip().lower()
    if choice in ["", "y", "yes"]:
        min_date = datetime.now() - timedelta(days=7)
        print(f"Анализ сообщений с {min_date.strftime('%Y-%m-%d %H:%M:%S')} до настоящего момента.")
    else:
        min_date = None
        print("Анализ сообщений за все время.")
    
    print(f"Поиск сообщений с хештегом {SEARCH_HASHTAG}...")
    data = await fetch_all_messages(client, SEARCH_HASHTAG, limit_per_dialog=1000, min_date=min_date)
    
    if not data:
        print(f"Сообщения с хештегом {SEARCH_HASHTAG} не найдены.")
    else:
        output_file = input("Введите имя выходного Excel файла (например, report.xlsx): ").strip()
        if not output_file:
            output_file = "report.xlsx"
        save_report(data, output_file)
    
    await client.disconnect()

if __name__ == '__main__':
    asyncio.run(main())