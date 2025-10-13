import asyncio
import json
import logging
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types, F
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder

TOKEN = "7818982442:AAGY-DDMsuvhLg0-Ec1ds43SkAmCltR88cI"
DATA_FILE = "data.json"
TELEGRAM_LINK = "https://t.me/sv010ch"
YOUR_TELEGRAM_ID = 487289287

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()
user_context = {}
students = {}
all_users = set()

def load_data():
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"schedule": []}

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_workdays(count=7):
    weekdays_ru = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница"]
    today = datetime.today()
    days = []
    current = today
    while len(days) < count:
        if current.weekday() < 5:  # только будни
            weekday_name = weekdays_ru[current.weekday()]
            days.append((weekday_name, current.strftime("%d.%m.%Y")))
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
    if message.from_user.id == YOUR_TELEGRAM_ID:
        buttons.insert(0, [InlineKeyboardButton(text="🛡 Админ-панель", callback_data="admin_panel")])
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    await message.answer(
        "👋 Привет! Я бот автоинструктора. Здесь ты можешь посмотреть расписание, записаться на занятие и отменить запись.",
        reply_markup=keyboard
    )

# --- Кнопочный выбор дня недели ---
@dp.callback_query(F.data == "add_record")
async def start_record(callback: types.CallbackQuery):
    builder = InlineKeyboardBuilder()
    for day_name, day_date in get_workdays(7):
        builder.button(text=f"{day_name}, {day_date}",
                       callback_data=f"select_day:{day_date}")
    builder.adjust(1)
    await callback.message.answer("📅 Выберите день занятия:", reply_markup=builder.as_markup())
    await callback.answer()

@dp.callback_query(F.data.startswith("select_day:"))
async def select_time(callback: types.CallbackQuery):
    day_date = callback.data.split(":")[1]
    user_id = callback.from_user.id
    if user_id not in user_context:
        user_context[user_id] = {}
    user_context[user_id]["date"] = day_date
    builder = InlineKeyboardBuilder()
    times = ["08:00", "09:20", "10:40", "12:50", "14:10", "15:30"]
    for t in times:
        builder.button(text=t, callback_data=f"select_time:{day_date}:{t}")
    builder.adjust(3)
    await callback.message.answer(f"🕒 Дата выбрана: {day_date}\nВыберите время занятия:", reply_markup=builder.as_markup())
    await callback.answer()

@dp.callback_query(F.data.startswith("select_time:"))
async def input_name_address(callback: types.CallbackQuery):
    _, day_date, time_sel = callback.data.split(":")
    user_id = callback.from_user.id
    if user_id not in user_context:
        user_context[user_id] = {}
    user_context[user_id]["date"] = day_date
    user_context[user_id]["time"] = time_sel
    await callback.message.answer("Введите фамилию, имя и адрес через запятую (например: Иванов Иван, Увельская 98):")
    await callback.answer()

@dp.message()
async def save_record(message: types.Message):
    user_id = message.from_user.id
    if user_id not in user_context or "date" not in user_context[user_id] or "time" not in user_context[user_id]:
        return  # не в процессе записи – игнорировать
    inp = message.text.strip().split(",", 1)
    if len(inp) != 2:
        await message.reply("Формат некорректен! Введите фамилию, имя и адрес через запятую.")
        return
    name_parts = inp[0].strip().split(" ", 1)
    if len(name_parts) != 2:
        await message.reply("Введите фамилию и имя через пробел, затем адрес через запятую!")
        return
    surname, name = name_parts
    address = inp[1].strip()
    date_s = user_context[user_id]["date"]
    time_s = user_context[user_id]["time"]
    data = load_data()
    data["schedule"].append({
        "date": date_s,
        "time": time_s,
        "name": name,
        "surname": surname,
        "address": address,
        "user_id": user_id
    })
    save_data(data)
    user_context.pop(user_id, None)
    await message.reply(f"✅ Запись сохранена: {date_s} {time_s} {surname} {name}, {address}")

# --- Пример панели админа (доработайте под свои задачи) ---
@dp.callback_query(F.data == "admin_panel")
async def admin_panel_button(callback: types.CallbackQuery):
    data = load_data()
    text = "<b>Все записи:</b>\n"
    for idx, item in enumerate(data["schedule"], 1):
        text += (f"{idx}. {item['date']} {item['time']} "
                 f"{item.get('surname','')} {item.get('name','')} "
                 f"{item.get('address','')}\n")
    await callback.message.answer(text)
    await callback.answer()

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
