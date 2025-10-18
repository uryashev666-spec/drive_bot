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
YOUR_TELEGRAM_ID = 487289287
DATA_FILE = "data.json"
USERS_FILE = "users_info.json"
TELEGRAM_LINK = "https://t.me/sv010ch"

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()
user_context = {}

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
        if len(time_s) == 2 and time_s.isdigit():
            try:
                return datetime.strptime(f"{date_s} {time_s}:00", "%d.%m.%Y %H:%M")
            except Exception:
                return None
        return None

def week_limit(user_id, date_str):
    data = load_data()
    target_day = datetime.strptime(date_str, "%d.%m.%Y")
    week_days = [(target_day + timedelta(days=i)).strftime("%d.%m.%Y") for i in range(7)]
    count = sum(1 for item in data["schedule"]
                if item.get("user_id") == user_id
                and item.get("date") in week_days
                and item.get("status") != "отменено")
    return count

@dp.message(Command("start"))
async def start(message: types.Message):
    buttons = [
        [InlineKeyboardButton(text="📅 Расписание", callback_data="view_schedule")],
        [InlineKeyboardButton(text="✏️ Записаться", callback_data="add_record")],
        [InlineKeyboardButton(text="💬 Написать инструктору", url=TELEGRAM_LINK)]
    ]
    if message.from_user.id == YOUR_TELEGRAM_ID:
        buttons.insert(0, [InlineKeyboardButton(text="🛡 Админ-панель", callback_data="admin_panel")])
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    await message.answer("👋 Привет! Я бот автоинструктора. Можешь посмотреть расписание и записаться на занятие.", reply_markup=keyboard)

@dp.callback_query(F.data == "add_record")
async def add_record(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    user_context[user_id] = {}
    data = load_data()
    builder = InlineKeyboardBuilder()
    for day_name, day_date in get_workdays(7):
        busy = any(item["date"] == day_date and item["user_id"] == user_id and item.get("status") != "отменено"
                   for item in data["schedule"])
        text = f"🚫 {day_name}, {day_date}" if busy else f"{day_name}, {day_date}"
        cdata = "user_busy_day" if busy else f"select_day:{day_date}"
        builder.button(text=text, callback_data=cdata)
    builder.adjust(1)
    await callback.message.answer("📅 Выберите день:", reply_markup=builder.as_markup())
    await callback.answer()

@dp.callback_query(F.data == "user_busy_day")
async def user_busy_day(callback: types.CallbackQuery):
    await callback.message.answer("На этот день вы уже записаны! Сначала отмените существующую запись.")
    await callback.answer()

@dp.callback_query(F.data.startswith("select_day:"))
async def select_time(callback: types.CallbackQuery):
    day_date = callback.data.split(":")[1]
    user_id = callback.from_user.id
    week_count = week_limit(user_id, day_date)
    if week_count >= 2:
        await callback.message.answer("Лимит: не более двух записей в неделю.")
        await callback.answer()
        return
    user_context[user_id] = {"date": day_date}
    data = load_data()
    builder = InlineKeyboardBuilder()
    for t in get_times():
        busy = any(item["date"] == day_date and item["time"] == t and item.get("status") != "отменено"
                   for item in data["schedule"])
        text = f"❌ {t}" if busy else t
        cdata = "busy" if busy else f"select_time:{t}"
        builder.button(text=text, callback_data=cdata)
    builder.adjust(3)
    await callback.message.answer(f"🕒 Дата выбрана: {day_date}\nВыберите время занятия:", reply_markup=builder.as_markup())
    await callback.answer()

@dp.callback_query(F.data == "busy")
async def busy_time(callback: types.CallbackQuery):
    await callback.message.answer("Это время уже занято.")
    await callback.answer()

@dp.callback_query(F.data.startswith("select_time:"))
async def select_time_write_name(callback: types.CallbackQuery):
    selected_time = callback.data[len('select_time:'):].strip()
    user_id = callback.from_user.id
    if user_id not in user_context:
        user_context[user_id] = {}
    if selected_time not in get_times():
        await callback.message.answer("Ошибка: некорректное время. Обновите меню!")
        return
    user_context[user_id]["time"] = selected_time
    if str(user_id) in users_info:
        ctx = user_context[user_id]
        ctx["surname"] = users_info[str(user_id)]["surname"]
        ctx["name"] = users_info[str(user_id)]["name"]
        user_context[user_id] = ctx
        await callback.message.answer("📍 Введите адрес, куда подъехать:")
    else:
        await callback.message.answer("👤 Введите фамилию и имя через пробел (например: Иванов Иван)")
    await callback.answer()

@dp.message()
async def process_name_or_address(message: types.Message):
    user_id = message.from_user.id
    ctx = user_context.get(user_id, {})
    if ctx.get("date") and ctx.get("time") and "name" not in ctx:
        parts = message.text.strip().split(" ", 1)
        if len(parts) < 2:
            await message.answer("Пожалуйста, напишите фамилию и имя через пробел.")
            return
        ctx["surname"], ctx["name"] = parts[0], parts[1]
        users_info[str(user_id)] = {"surname": ctx["surname"], "name": ctx["name"]}
        save_users_info(users_info)
        user_context[user_id] = ctx
        await message.answer("📍 Введите адрес, куда подъехать:")
        return
    if ctx.get("date") and ctx.get("time") and ctx.get("name") and "address" not in ctx:
        ctx["address"] = message.text.strip()
        user_context[user_id] = ctx
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Подтвердить запись", callback_data="confirm_record")]
        ])
        await message.answer(
           f"Записать на {ctx['date']} {ctx['time']}\nФИО: {ctx['surname']} {ctx['name']}\nАдрес: {ctx['address']}\nНажмите «Подтвердить запись».",
           reply_markup=kb)
        return

@dp.callback_query(F.data == "confirm_record")
async def confirm_record(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    ctx = user_context.get(user_id, {})
    if not (ctx.get("date") and ctx.get("time") and ctx.get("name") and ctx.get("address")):
        await callback.message.answer("Ошибка: не хватает данных для записи.")
        await callback.answer()
        return
    week_count = week_limit(user_id, ctx["date"])
    if week_count >= 2:
        await callback.message.answer("Лимит: не более двух записей в неделю.")
        await callback.answer()
        return
    data = load_data()
    data["schedule"].append({
        "date": ctx["date"],
        "time": ctx["time"],
        "name": ctx["name"],
        "surname": ctx["surname"],
        "address": ctx["address"],
        "user_id": user_id
    })
    save_data(data)
    await callback.message.answer("✅ Запись подтверждена и сохранена!")
    user_context.pop(user_id, None)
    await start(callback.message)
    await callback.answer()

@dp.callback_query(F.data == "view_schedule")
async def view_schedule(callback: types.CallbackQuery):
    data = load_data()
    now = datetime.now()
    my_id = callback.from_user.id
    my_records = [
        item for item in data["schedule"]
        if item.get("user_id") == my_id and item.get("status") != "отменено"
           and safe_datetime(item['date'], item['time']) and safe_datetime(item['date'], item['time']) > now
    ]
    my_records.sort(key=lambda item: safe_datetime(item['date'], item['time']) or datetime.max)
    text = ""
    builder = InlineKeyboardBuilder()
    for idx, item in enumerate(my_records):
        text += f"🟢 Моя запись {idx+1}:\nДата: {item['date']}\nВремя: {item['time']}\nАдрес: {item['address']}\n"
        builder.button(
            text=f"❌ Отменить {item['date']} {item['time']}",
            callback_data=f"user_cancel:{item['date']}:{item['time']}"
        )
    if not text:
        text = "У вас нет записей на ближайшее время."
    builder.adjust(1)
    await callback.message.answer(text, reply_markup=builder.as_markup())
    await callback.answer()

@dp.callback_query(F.data.startswith("user_cancel:"))
async def user_cancel(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    prefix = "user_cancel:"
    rest = callback.data[len(prefix):]
    date_s, time_s = rest.split(":", 1)
    data = load_data()
    found = next((item for item in data["schedule"] if
                  item["date"]==date_s and item["time"]==time_s and item.get("user_id")==user_id and item.get("status")!="отменено"), None)
    if not found:
        await callback.message.answer("Запись не найдена.")
        await callback.answer()
        return
    found["status"] = "отменено"
    save_data(data)
    await callback.message.answer(f"✅ Ваша запись {date_s} {time_s} отменена! Все получат уведомление о свободном времени.")
    all_users = set(item["user_id"] for item in data["schedule"]) | {user_id}
    for uid in all_users:
        if uid != user_id:
            try:
                await bot.send_message(
                    uid,
                    f"🔔 Освободилось время занятий!\nДата: {date_s}\nВремя: {time_s}\nМожете записаться!"
                )
            except Exception:
                pass
    await callback.answer()

@dp.callback_query(F.data == "admin_panel")
async def admin_panel(callback: types.CallbackQuery):
    if callback.from_user.id != YOUR_TELEGRAM_ID:
        await callback.message.answer('⛔ Только для администратора!')
        await callback.answer()
        return
    data = load_data()
    now = datetime.now()
    upcoming_days = sorted(set(
        item["date"]
        for item in data["schedule"]
        if safe_datetime(item["date"], item["time"]) and safe_datetime(item["date"], item["time"]) > now
    ))
    builder = InlineKeyboardBuilder()
    text = "<b>АДМИНИСТРАТОР: Управление занятиями</b>\n\n"
    for day in upcoming_days:
        builder.button(text=f"❌ Закрыть все занятия на {day}", callback_data=f"admin_cancel_day_close:{day}")

    # slots отмена отдельного занятия
    upcoming_slots = [
        item for item in data["schedule"]
        if item.get("status") != "отменено"
           and safe_datetime(item["date"], item["time"])
           and safe_datetime(item["date"], item["time"]) > now
    ]
    for idx, slot in enumerate(upcoming_slots, 1):
        day = slot["date"]
        time = slot["time"]
        uid = slot["user_id"]
        name = slot.get("surname", "") + " " + slot.get("name", "")
        address = slot.get("address", "")
        text += f"\n{idx}. {day} {time} — {name}, {address}\n"
        builder.button(
            text=f"Освободить {day} {time}",
            callback_data=f"admin_cancel_slot:{day}:{time}:{uid}:free"
        )
        builder.button(
            text=f"Закрыть {day} {time}",
            callback_data=f"admin_cancel_slot:{day}:{time}:{uid}:nofree"
        )
    builder.adjust(2)
    await callback.message.answer(text, reply_markup=builder.as_markup())
    await callback.answer()

@dp.callback_query(F.data.startswith("admin_cancel_slot:"))
async def admin_cancel_slot(callback: types.CallbackQuery):
    prefix = "admin_cancel_slot:"
    rest = callback.data[len(prefix):]
    parts = rest.rsplit(":", 2)
    day_time = parts[0]
    cancel_id = parts[1]
    cancel_type = parts[2]
    day, slot_time = day_time.split(":", 1)
    slot_time = slot_time.strip()
    data = load_data()
    slot = next((item for item in data["schedule"] if item["date"] == day and item["time"].strip() == slot_time and str(item["user_id"]) == cancel_id and item.get("status") != "отменено"), None)
    if not slot:
        await callback.message.answer("Слот не найден.")
        await callback.answer()
        return
    slot["status"] = "отменено"
    save_data(data)
    try:
        if cancel_type == "free":
            await bot.send_message(int(cancel_id), f"⛔ Ваше занятие {day} {slot_time} отменено, слот освобожден для других учеников.")
            await callback.message.answer("Слот отменён и освобождён (станет доступен другим).")
        else:
            await bot.send_message(int(cancel_id), f"⛔ Занятие отменено в связи с технической необходимостью")
            await callback.message.answer("Слот отменён и закрыт (для других не будет доступен).")
    except Exception:
        pass
    await callback.answer()

@dp.callback_query(F.data.startswith("admin_cancel_day_close:"))
async def admin_cancel_day_close(callback: types.CallbackQuery):
    _, day = callback.data.split(":")
    data = load_data()
    cancelled = 0
    for slot in data["schedule"]:
        if slot.get("date") == day and slot.get("status") != "отменено":
            slot["status"] = "отменено"
            cancelled += 1
            try:
                await bot.send_message(
                    slot["user_id"],
                    "⛔ Занятие отменено в связи с технической необходимостью"
                )
            except Exception:
                pass
    save_data(data)
    await callback.message.answer(f"❌ Все занятия на {day} отменены и слоты закрыты. Сообщение отправлено {cancelled} ученикам.")
    await callback.answer()

async def send_reminders():
    while True:
        now = datetime.now()
        data = load_data()
        for item in data["schedule"]:
            if item.get("status") == "отменено":
                continue
            session_time = safe_datetime(item["date"], item["time"])
            if session_time:
                if abs((session_time - now).total_seconds() - 86400) < 60:
                    try:
                        await bot.send_message(
                            item["user_id"], 
                            f"🔔 Напоминание: занятие завтра в {item['time']} ({item['date']})"
                        )
                    except Exception:
                        pass
                if 0 < (session_time - now).total_seconds() <= 1200:
                    try:
                        await bot.send_message(
                            item["user_id"], 
                            f"⏰ Напоминание: занятие через 20 минут!"
                        )
                    except Exception:
                        pass
        await asyncio.sleep(60)

async def main():
    asyncio.create_task(send_reminders())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
