import asyncio
import re
import sys
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError
import pandas as pd
from datetime import datetime, timedelta

api_id = 12345678
api_hash = 'your_api_hash_here'
session_name = 'my_session'
hashtag_pattern = re.compile(r'#\w+')

async def authorize(client):
    await client.connect()
    if not await client.is_user_authorized():
        phone = input("📱 Введите номер телефона: ").strip()
        await client.send_code_request(phone)
        code = input("🔑 Введите код подтверждения: ").strip()
        try:
            await client.sign_in(phone, code=code)
        except SessionPasswordNeededError:
            pwd = input("🔒 Введите пароль 2FA: ").strip()
            await client.sign_in(password=pwd)
    print("✅ Авторизация успешна")

async def fetch_all_messages(client, target_hashtag=None, limit_per_dialog=1000, min_date=None):
    results = []
    dialogs = await client.get_dialogs()
    if min_date:
        naive_min = min_date.replace(tzinfo=None)
    for dlg in dialogs:
        msgs = await client.get_messages(dlg.entity, limit=limit_per_dialog)
        if min_date:
            msgs = [m for m in msgs if m.date and m.date.replace(tzinfo=None) >= naive_min]
        for m in msgs:
            if not m.text:
                continue
            tags = hashtag_pattern.findall(m.text)
            if target_hashtag:
                if target_hashtag not in tags:
                    continue
            else:
                if not tags:
                    continue
            results.append({
                "chat_name": dlg.name or str(dlg.id),
                "chat_id": dlg.id,
                "date": m.date.replace(tzinfo=None),
                "text": m.text.strip(),
                "hashtags": ", ".join(tags)
            })
    return results

def save_report(data, filename):
    df = pd.DataFrame(data)
    df['date'] = pd.to_datetime(df['date']).dt.tz_localize(None)
    df['day']   = df['date'].dt.date
    df['week']  = df['date'].dt.strftime("%Y-%U")
    df['month'] = df['date'].dt.strftime("%Y-%m")
    df['year']  = df['date'].dt.strftime("%Y")
    df.to_excel(filename, index=False)
    print(f"💾 Отчёт сохранён в файл: {filename}")

async def main():
    client = TelegramClient(session_name, api_id, api_hash)
    await authorize(client)

    choice = input("🏷️ Искать конкретный хештег? (Y/n): ").strip().lower()
    if choice in ("y", ""):
        tag = input("🏷️ Введите хештег: ").strip()
        if not tag.startswith("#"):
            tag = "#" + tag
        target = tag
    else:
        target = None

    choice2 = input("⏱️ Только последние 7 дней? (Y/n): ").strip().lower()
    if choice2 in ("y", ""):
        min_date = datetime.now() - timedelta(days=7)
    else:
        min_date = None

    print("🔍 Поиск сообщений...")
    data = await fetch_all_messages(client, target, 1000, min_date)
    await client.disconnect()

    if not data:
        print("⚠️ Сообщений не найдено")
        return

    fn = input("📂 Имя файла для сохранения (report.xlsx): ").strip()
    if not fn.lower().endswith(".xlsx"):
        fn = "report.xlsx"
    save_report(data, fn)

if __name__ == "__main__":
    asyncio.run(main())