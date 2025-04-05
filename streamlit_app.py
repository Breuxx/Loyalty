import streamlit as st
import nest_asyncio
import re
import asyncio
from datetime import datetime, timedelta
import os
from telethon import TelegramClient

# Применяем nest_asyncio для поддержки вложенных event loops
nest_asyncio.apply()

# Создаём или получаем event loop вручную
try:
    loop = asyncio.get_running_loop()
except RuntimeError:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

# ---------------------------
# Конфигурация для Telegram API
# ---------------------------
api_id = '1403467'  # Ваш API ID
api_hash = '15525849e4b493d2143b175f96825f87'  # Ваш API hash
session_name = 'my_session'  # Имя файла сессии

# Регулярное выражение для поиска хештегов
hashtag_pattern = re.compile(r'#\w+')

# Функция для создания клиента Telethon с указанием текущего event loop
def create_client():
    try:
        current_loop = asyncio.get_running_loop()
    except RuntimeError:
        current_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(current_loop)
    return TelegramClient(session_name, api_id, api_hash, loop=current_loop)

# ---------------------------
# Асинхронные функции для работы с Telegram
# ---------------------------
async def get_dialogs(client):
    dialogs = await client.get_dialogs()
    return [{"name": d.name, "id": d.id} for d in dialogs]

async def fetch_messages(client, entity, limit=1000):
    messages = await client.get_messages(entity, limit=limit)
    return messages

# Функция для извлечения сообщений с хештегами
def extract_hashtag_messages(messages, target_hashtag=None):
    filtered = []
    for msg in messages:
        if msg.text:
            hashtags = hashtag_pattern.findall(msg.text)
            if target_hashtag:
                if target_hashtag in hashtags:
                    filtered.append((msg.date, msg.text, hashtags))
            else:
                if hashtags:
                    filtered.append((msg.date, msg.text, hashtags))
    return filtered

# Функция для подсчёта отчёта
def get_report(messages):
    now = datetime.now(messages[0][0].tzinfo) if messages else datetime.now()
    one_day = now - timedelta(days=1)
    one_week = now - timedelta(weeks=1)
    one_month = now - timedelta(days=30)
    msgs_day = [m for m in messages if m[0] >= one_day]
    msgs_week = [m for m in messages if m[0] >= one_week]
    msgs_month = [m for m in messages if m[0] >= one_month]
    return {"day": len(msgs_day), "week": len(msgs_week), "month": len(msgs_month)}

# ---------------------------
# Основное Streamlit-приложение
# ---------------------------
def main():
    st.title("Telegram Tracker")

    st.sidebar.header("Настройки авторизации")
    phone = st.sidebar.text_input("Введите номер телефона (или токен бота):")
    if not phone:
        st.info("Введите номер телефона для продолжения.")
        return

    # Создаем клиента и запускаем его
    client = create_client()
    try:
        loop.run_until_complete(client.start(phone=phone))
    except Exception as e:
        st.error(f"Ошибка при запуске клиента: {e}")
        return

    st.success("Клиент успешно запущен!")

    if st.button("Получить список диалогов"):
        dialogs = loop.run_until_complete(get_dialogs(client))
        st.write("Доступные диалоги:")
        for dialog in dialogs:
            st.write(f"{dialog['name']} (ID: {dialog['id']})")
    
    entity = st.text_input("Введите ID или username диалога для отчёта:")
    search_command = st.text_input("Введите команду поиска (www или w#<хештег>):")
    
    if st.button("Сформировать отчёт"):
        if not entity or not search_command:
            st.error("Укажите диалог и команду поиска.")
        else:
            messages = loop.run_until_complete(fetch_messages(client, entity))
            if search_command.startswith("www"):
                hash_messages = extract_hashtag_messages(messages)
            elif search_command.startswith("w#"):
                tag = search_command[2:]
                if not tag.startswith("#"):
                    tag = "#" + tag
                hash_messages = extract_hashtag_messages(messages, target_hashtag=tag)
            else:
                st.error("Неверная команда поиска.")
                return
            
            if hash_messages:
                report_data = get_report(hash_messages)
                st.subheader("Отчёт:")
                st.write(f"За день: {report_data['day']}")
                st.write(f"За неделю: {report_data['week']}")
                st.write(f"За месяц: {report_data['month']}")
                st.subheader("Сообщения:")
                for date, text, tags in hash_messages:
                    st.write(f"{date.strftime('%Y-%m-%d %H:%M:%S')}: {text}")
            else:
                st.info("Сообщения не найдены.")
    
    if st.button("Отключить клиента"):
        loop.run_until_complete(client.disconnect())
        st.info("Клиент отключен.")

if __name__ == '__main__':
    main()