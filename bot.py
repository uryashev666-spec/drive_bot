import asyncio
import json
import logging
import os
import sys
import aiohttp
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types, F
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton, CallbackQuery
from aiogram.filters import Command

TOKEN = "7818982442:AAGY-DDMsuvhLg0-Ec1ds43SkAmCltR88cI"
YOUR_TELEGRAM_ID = 487289287
DATA_FILE = "data.json"
USERS_FILE = "users_info.json"
TELEGRAM_LINK = "https://t.me/sv010ch"
GITHUB_RAW_URL = "https://raw.githubusercontent.com/uryashev666-spec/drive_bot/main/bot.py"
logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()
user_context = {}

# --- Reply-клавиатура, генератор с проверкой на админа ---
def get_main_menu_kb(user_id):
    buttons = [
        [KeyboardButton(text="📅 Моё расписание")],
        [KeyboardButton(text="✏️ Записаться")],
        [KeyboardButton(text="💬 Инструктор")]
    ]
    if user_id == YOUR_TELEGRAM_ID:
        buttons.insert(0, [KeyboardButton(text="🛡 Админ-панель")])
    return ReplyKeyboardMarkup(
        keyboard=buttons,
        resize_keyboard=True,
        one_time_keyboard=False
    )

def load_data():
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"schedule": []}

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_users_info():
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_users_info(info):
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(info, f, ensure_ascii=False, indent=2)

users_info = load_users_info()

def get_workdays(count=10):
    weekdays_ru = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница"]
    today = datetime.today()
    days = []
    current = today
    while len(days) < count:
        if current.weekday() < 5:
            days.append((weekdays_ru[current.weekday()], current.strftime("%d.%m.%Y")))
        current += timedelta(days=1)
    return days

def get_times():
    return ["08:00", "09:20", "10:40", "12:50", "14:10", "15:30"]

def safe_datetime(date_s, time_s):
    try:
        return datetime.strptime(f"{date_s} {time_s}", "%d.%m.%Y %H:%M")
    except Exception:
        return None

def week_limit(user_id, new_date):
    data = load_data()
    new_dt = datetime.strptime(new_date, "%d.%m.%Y")
    week_dates = [(new_dt + timedelta(days=i)).strftime("%d.%m.%Y") for i in range(-6, 1)]
    return sum(
        1 for item in data["schedule"]
        if item.get("user_id") == user_id
        and item.get("date") in week_dates
        and item.get("status") != "отменено"
    )

async def send_user_schedule(message: types.Message, user_id: int):
    data = load_data()
    now = datetime.now()
    my_records = [
        item for item in data["schedule"]
        if item.get("user_id") == user_id and item.get("status") != "отменено"
        and safe_datetime(item['date'], item['time']) and safe_datetime(item['date'], item['time']) > now
    ]
    my_records.sort(key=lambda item: safe_datetime(item['date'], item['time']) or datetime.max)
    text = ""
    builder = []
    for idx, item in enumerate(my_records):
        text += f"🟢 Моя запись {idx+1}:\nДата: {item['date']}\nВремя: {item['time']}\nАдрес: {item['address']}\n"
        builder.append([InlineKeyboardButton(
            text=f"❌ Отменить {item['date']} {item['time']}",
            callback_data=f"user_cancel:{item['date']}:{item['time']}"
        )])
    if not text:
        text = "У вас нет записей на ближайшее время."
    keyboard = InlineKeyboardMarkup(inline_keyboard=builder) if builder else None
    await message.answer(text, reply_markup=keyboard if keyboard else None)

async def start_add_record_flow(message: types.Message):
    user_id = message.from_user.id
    user_context[user_id] = {}
    data = load_data()
    builder = []
    for day_name, day_date in get_workdays(10):
        week_count = week_limit(user_id, day_date)
        if week_count >= 2:
            text = f"🚫 {day_name}, {day_date} (лимит)"
            cdata = "user_over_limit"
        else:
            busy = any(item["date"] == day_date and item["user_id"] == user_id and item.get("status") != "отменено"
                       for item in data["schedule"])
            text = f"🚫 {day_name}, {day_date}" if busy else f"{day_name}, {day_date}"
            cdata = "user_busy_day" if busy else f"select_day:{day_date}"
        builder.append([InlineKeyboardButton(text=text, callback_data=cdata)])
    keyboard = InlineKeyboardMarkup(inline_keyboard=builder)
    await message.answer("📅 Выберите день:", reply_markup=keyboard)

@dp.callback_query(F.data == "user_over_limit")
async def user_over_limit(callback: types.CallbackQuery):
    await callback.message.answer("⛔ Вы уже записаны 2 раза за 7 дней, запись на выбранные дни данной недели недоступна. Попробуйте выбрать день следующей недели!")
    await callback.answer()

@dp.message(Command("start"))
async def start(message: types.Message):
    buttons = [
        [InlineKeyboardButton(text="📅 Моё расписание", callback_data="view_schedule")],
        [InlineKeyboardButton(text="✏️ Записаться", callback_data="add_record")],
        [InlineKeyboardButton(text="💬 Написать инструктору", url=TELEGRAM_LINK)]
    ]
    if message.from_user.id == YOUR_TELEGRAM_ID:
        buttons.insert(0, [InlineKeyboardButton(text="🛡 Админ-панель", callback_data="admin_panel")])
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    await message.answer(
        "👋 Привет! Я бот автоинструктора. Можешь посмотреть расписание и записаться на занятие.",
        reply_markup=get_main_menu_kb(message.from_user.id)  # <--- изменено!
    )
    await message.answer("Меню управления:", reply_markup=keyboard)

@dp.message()
async def handler_menu_and_input(message: types.Message):
    text = message.text.strip()
    if text == "🛡 Админ-панель" and message.from_user.id == YOUR_TELEGRAM_ID:
        # Симуляция callback для админа
        fake_callback = CallbackQuery(
            id="admin_panel_btn",
            from_user=message.from_user,
            message=message,
            data="admin_panel",
            chat_instance="fake"
        )
        await admin_panel(fake_callback)
        return
    if text == "📅 Моё расписание":
        await send_user_schedule(message, message.from_user.id)
        return
    elif text == "✏️ Записаться":
        await start_add_record_flow(message)
        return
    elif text == "💬 Инструктор":
        await message.answer("Вы можете написать инструктору: " + TELEGRAM_LINK)
        return
    await process_name_or_address(message)

# --- далее остальной код (админ-панель, функции и обработчики) оставь БЕЗ изменений! ---
# --- весь старый раздел с InlineAdmin, черновиком и прочим твой код ---

# END
