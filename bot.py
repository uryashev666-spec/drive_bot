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
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📅 Расписание", callback_data="view_schedule")],
            [InlineKeyboardButton(text="✏️ Записаться", callback_data="add_record")],
            [InlineKeyboardButton(text="💬 Написать инструктору", url=TELEGRAM_LINK)]
        ]
    )
    await message.answer(
        "👋 Привет! Я бот автоинструктора. Здесь ты можешь посмотреть расписание и записаться на занятие.",
        reply_markup=keyboard
    )

@dp.callback_query(F.data == "view_schedule")
async def view_schedule(callback: types.CallbackQuery):
    data = load_data()
    user_id = callback.from_user.id
    my_records = [item for item in data["schedule"] if item.get("user_id")==user_id and item.get("status")!="отменено"]
    other_records = [item for item in data["schedule"] if item.get("user_id")!=user_id and item.get("status")!="отменено"]

    text = ""
    builder = InlineKeyboardBuilder()
    for idx, item in enumerate(my_records):
        text += f"🟢 Моя запись {idx+1}:\nДата: {item['date']}\nВремя: {item['time']}\nАдрес: {item['address']}\n"
        builder.button(text=f"❌ Отменить {item['date']} {item['time']}", callback_data=f"cancel_my_record:{item['date']}:{item['time']}")
    if other_records:
        text += "\n🟡 Другие записи:\n" + "\n".join(
            f"• {item['date']}, {item['time']}, {item.get('name','')} {item.get('surname','')}, {item.get('address','')}"
            for item in other_records
        )
    builder.adjust(1)
    await callback.message.answer(text or "Нет записей.", reply_markup=builder.as_markup())
    await callback.answer()

@dp.callback_query(F.data.startswith("cancel_my_record:"))
async def cancel_my_record(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    _, date_s, time_s = callback.data.split(":", 2)
    data = load_data()
    now = datetime.now()
    dt_slot = datetime.strptime(f"{date_s} {time_s}", "%d.%m.%Y %H:%M")
    hours_left = (dt_slot - now).total_seconds() / 3600
    found = next((item for item in data["schedule"] if
                  item["date"]==date_s and item["time"]==time_s and item["user_id"]==user_id and item.get("status")!="отменено"), None)
    if not found:
        await callback.message.answer("Запись не найдена.")
        await callback.answer()
        return
    if hours_left < 12:
        await callback.message.answer("Отменить запись через бота поздно (меньше 12 часов). Свяжитесь с инструктором!")
        await callback.answer()
        return
    found["status"] = "отменено"
    save_data(data)
    await callback.message.answer(f"✅ Запись {date_s} {time_s} отменена! Другим пользователям отправлено уведомление о свободном времени.")
    for uid in all_users:
        if uid != user_id:
            try:
                await bot.send_message(
                    uid,
                    f"🔔 Освободилось время занятий!\nДата: {date_s}\nВремя: {time_s}\nМожно записаться!"
                )
            except Exception:
                pass
    await callback.answer()

@dp.callback_query(F.data == "add_record")
async def add_record(callback: types.CallbackQuery):
    days = get_workdays(10)
    data = load_data()
    times_list = ["8:00", "9:20", "10:40", "12:50", "14:10", "15:30"]
    builder = InlineKeyboardBuilder()
    for day_name, d in days:
        busy_count = 0
        for t in times_list:
            busy = any(
                item["date"] == d and item["time"] == t and item.get("status") != "отменено"
                for item in data["schedule"])
            if busy:
                busy_count += 1
        if busy_count == len(times_list):
            builder.button(text=f"❌ {day_name}, {d}", callback_data="busy_day")
        else:
            builder.button(text=f"{day_name}, {d}", callback_data=f"select_day:{d}")
    builder.adjust(1)
    await callback.message.answer("📅 Выберите день занятия:", reply_markup=builder.as_markup())
    await callback.answer()

@dp.callback_query(F.data.startswith("select_day:"))
async def select_day(callback: types.CallbackQuery):
    selected_date = callback.data.split(":", 1)[1]
    user_id = callback.from_user.id
    all_users.add(user_id)
    user_context[user_id] = {"date": selected_date}
    times_list = ["8:00", "9:20", "10:40", "12:50", "14:10", "15:30"]
    data = load_data()
    builder = InlineKeyboardBuilder()
    for t in times_list:
        busy = any(
            item["date"] == selected_date and item["time"] == t and item.get("status") != "отменено"
            for item in data["schedule"])
        if busy:
            builder.button(text=f"❌ {t}", callback_data="busy")
        else:
            builder.button(text=t, callback_data=f"select_time:{t}")
    builder.adjust(3)
    await callback.message.answer(
        f"🕒 Дата выбрана: {selected_date}\nВыберите время занятия:",
        reply_markup=builder.as_markup()
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("select_time:"))
async def select_time(callback: types.CallbackQuery, state: FSMContext):
    selected_time = callback.data.split(":", 1)[1]
    user_id = callback.from_user.id
    user_context[user_id] = user_context.get(user_id, {})
    user_context[user_id]["time"] = selected_time
    await callback.message.answer("👤 Введите ВАШИ фамилию и имя через пробел (например: Иванов Иван)")
    await state.set_state(Booking.waiting_for_name)
    await callback.answer()

@dp.message(Booking.waiting_for_name)
async def process_name(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    parts = message.text.strip().split()
    if len(parts) < 2:
        await message.answer("Пожалуйста, укажите фамилию и имя через пробел.")
        return
    user_context[user_id]["name"] = parts[1]
    user_context[user_id]["surname"] = parts[0]
    await message.answer("📍 Введите адрес, куда подъехать:")
    await state.set_state(Booking.waiting_for_address)

@dp.message(Booking.waiting_for_address)
async def process_address(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    user_context[user_id]["address"] = message.text.strip()
    uc = user_context[user_id]
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Подтвердить запись", callback_data="confirm_entry")
    builder.button(text="❌ Отменить занятие", callback_data="user_cancel")
    await message.answer(
        f"🟢 Ваша запись:\n"
        f"Фамилия: {uc['surname']}\n"
        f"Имя: {uc['name']}\n"
        f"Адрес: {uc['address']}\n"
        f"Дата: {uc['date']}\n"
        f"Время: {uc['time']}\n"
        "Нажмите кнопку ниже для подтверждения.",
        reply_markup=builder.as_markup()
    )
    await state.clear()

# ... далее все функции и админ-панель без изменений ...

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
