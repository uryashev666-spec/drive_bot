import asyncio
import json
import logging
from datetime import datetime, date, timedelta
from aiogram import Bot, Dispatcher, types, F
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext

TOKEN = "7818982442:AAGY-DDMsuvhLg0-Ec1ds43SkAmCltR88cI"
DATA_FILE = "data.json"
TELEGRAM_LINK = "https://t.me/sv010ch"
YOUR_TELEGRAM_ID = 487289287

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()
user_context = {}
all_users = set()
students = {}  # user_id: {"surname": ..., "name": ...}

class Booking(StatesGroup):
    waiting_for_name = State()
    waiting_for_address = State()

def load_data():
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"schedule": []}

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_user_week_records(schedule, user_id):
    now = datetime.now()
    return [
        item for item in schedule if item.get("user_id") == user_id
            and 0 <= (now - datetime.strptime(item.get("date"), "%d.%m.%Y")).days < 7
    ]

def get_workdays(count=10):
    weekdays_ru = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница"]
    now = datetime.now()
    today = date.today()
    days = []
    current = today
    skip_today = (now.hour > 15) or (now.hour == 15 and now.minute >= 20)
    added = 0
    while added < count:
        if current.weekday() < 5:
            if skip_today and current == today:
                current += timedelta(days=1)
                skip_today = False
                continue
            day_name = weekdays_ru[current.weekday()]
            days.append((day_name, current.strftime("%d.%m.%Y")))
            added += 1
        current += timedelta(days=1)
    return days

@dp.message(Command("start"))
async def start(message: types.Message):
    all_users.add(message.from_user.id)
    buttons = [
        [InlineKeyboardButton(text="📅 Расписание", callback_data="view_schedule")],
        [InlineKeyboardButton(text="✏️ Записаться", callback_data="add_record")],
        [InlineKeyboardButton(text="💬 Написать инструктору", url=TELEGRAM_LINK)]
    ]
    # Только для админа добавить кнопку!
    if message.from_user.id == YOUR_TELEGRAM_ID:
        buttons.insert(0, [InlineKeyboardButton(text="🛡 Админ-панель", callback_data="admin_panel")])
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    await message.answer(
        "👋 Привет! Я бот автоинструктора. Здесь ты можешь посмотреть расписание и записаться на занятие.",
        reply_markup=keyboard
    )

@dp.callback_query(F.data == "admin_panel")
async def admin_panel_button(callback: types.CallbackQuery):
    await admin_panel(callback.message)
    await callback.answer()

@dp.message(Command('admin'))
async def admin_panel(message: types.Message):
    if message.from_user.id != YOUR_TELEGRAM_ID:
        await message.answer('⛔ Только для администратора!')
        return

    data = load_data()
    now = datetime.now()
    all_records = [
        item for item in data["schedule"]
        if item.get("status") != "отменено"
        and datetime.strptime(f"{item['date']} {item['time']}", "%d.%m.%Y %H:%M") > now
    ]
    all_records.sort(key=lambda item: datetime.strptime(f"{item['date']} {item['time']}", "%d.%m.%Y %H:%M"))

    text = "👑 <b>Админ-панель</b>\n"
    builder = InlineKeyboardBuilder()
    for idx, item in enumerate(all_records):
        text += (
            f"\n🔹 {idx+1}. Дата: {item['date']} Время: {item['time']}\n"
            f"Фамилия: {item.get('surname','')}\nИмя: {item.get('name','')}\nАдрес: {item.get('address','')}\n"
            f"ID ученика: {item['user_id']}\n"
        )
        builder.button(
            text=f"❌ Отменить {item['date']} {item['time']} [{item['user_id']}]",
            callback_data=f"admin_cancel:{item['date']}:{item['time']}:{item['user_id']}"
        )
    builder.adjust(1)
    await message.answer(text, reply_markup=builder.as_markup())


@dp.callback_query(F.data.startswith("admin_cancel:"))
async def admin_cancel(callback: types.CallbackQuery):
    if callback.from_user.id != YOUR_TELEGRAM_ID:
        await callback.message.answer("⛔ Только для администратора!")
        await callback.answer()
        return
    _, date_s, time_s, target_id = callback.data.split(":", 3)
    data = load_data()
    found = next((item for item in data["schedule"] if
                  item["date"]==date_s and item["time"]==time_s and str(item["user_id"])==str(target_id) and item.get("status")!="отменено"), None)
    if not found:
        await callback.message.answer("Запись не найдена.")
        await callback.answer()
        return
    found["status"] = "отменено"
    save_data(data)
    await callback.message.answer(f"✅ Запись {date_s} {time_s} пользователя {target_id} отменена!")
    try:
        await bot.send_message(int(target_id),
            f"⚠️ Ваша запись на {date_s} {time_s} была отменена администратором.")
    except Exception:
        pass
    await callback.answer()

# ...дальше код пользователя, ограничения, подтверждение записи и т.д...
# (оставьте весь остальной обработчик расписания, add_record, select_day, select_time, confirm_entry и другие ровно как раньше —
# в этой части ничего менять не нужно)
