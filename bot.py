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
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
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

# Главное меню (ReplyKeyboardMarkup)
main_menu_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📅 Моё расписание")],
        [KeyboardButton(text="✏️ Записаться")],
        [KeyboardButton(text="💬 Инструктор")]
    ],
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

# ====== ФУНКЦИИ-КОМПОНЕНТЫ ДЛЯ ПОВТОРНОГО ИСПОЛЬЗОВАНИЯ ======
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
    await message.answer(text, reply_markup=keyboard if keyboard else main_menu_kb)

async def start_add_record_flow(message: types.Message):
    user_id = message.from_user.id
    user_context[user_id] = {}
    data = load_data()
    builder = []
    for day_name, day_date in get_workdays(10):
        # Новый: лимитируем не по дате вызова, а по дате слота!
        week_count = week_limit(user_id, day_date)
        if week_count >= 2:
            # Запрет на запись – покажем как недоступный
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
    await callback.message.answer("⛔ Вы уже записаны 2 раза за 7 дней, запись на выбранные дни данной недели недоступна. Попробуйте выбрать день следующей недели!", reply_markup=main_menu_kb)
    await callback.answer()

# ========== ОБРАБОТЧИКИ КОМАНДЫ /start ==========
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
        reply_markup=main_menu_kb
    )
    await message.answer("Меню управления:", reply_markup=keyboard)

# ========== ГЛАВНОЕ МЕНЮ И ОБРАБОТКА ВВОДА ==========
@dp.message()
async def handler_menu_and_input(message: types.Message):
    text = message.text.strip()
    if text == "📅 Моё расписание":
        await send_user_schedule(message, message.from_user.id)
        return
    elif text == "✏️ Записаться":
        await start_add_record_flow(message)
        return
    elif text == "💬 Инструктор":
        await message.answer("Вы можете написать инструктору: " + TELEGRAM_LINK)
        return
    # Всё остальное: ФИО, адрес, старый ввод
    await process_name_or_address(message)

# ====== ОБРАБОТЧИКИ INLINE-КНОПОК (callback_query) =======
@dp.callback_query(F.data == "add_record")
async def add_record(callback: types.CallbackQuery):
    await start_add_record_flow(callback.message)
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
        await callback.message.answer("Лимит: не более двух занятий в неделю для ученика. Запишитесь на другую неделю!", reply_markup=main_menu_kb)
        await callback.answer()
        return
    user_context[user_id] = {"date": day_date}
    data = load_data()
    builder = []
    for t in get_times():
        busy = any(item["date"] == day_date and item["time"] == t and item.get("status") != "отменено"
                   for item in data["schedule"])
        text = f"❌ {t}" if busy else t
        cdata = "busy" if busy else f"select_time:{t}"
        builder.append([InlineKeyboardButton(text=text, callback_data=cdata)])
    keyboard = InlineKeyboardMarkup(inline_keyboard=builder)
    await callback.message.answer(f"🕒 Дата выбрана: {day_date}\nВыберите время занятия:", reply_markup=keyboard)
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
        await callback.message.answer("Ошибка: не хватает данных для записи.", reply_markup=main_menu_kb)
        await callback.answer()
        return
    week_count = week_limit(user_id, ctx["date"])
    if week_count >= 2:
        await callback.message.answer("Лимит: не более двух занятий для ученика за семь дней подряд.", reply_markup=main_menu_kb)
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
    card_text = (
        f"🚗 <b>Новая запись!</b>\n"
        f"Дата: <b>{ctx['date']}</b>\n"
        f"Время: <b>{ctx['time']}</b>\n"
        f"ФИО: <b>{ctx['surname']} {ctx['name']}</b>\n"
        f"Адрес: <b>{ctx['address']}</b>"
    )
    try:
        await bot.send_message(YOUR_TELEGRAM_ID, card_text, parse_mode="HTML")
    except Exception:
        pass
    await callback.message.answer("✅ Запись подтверждена и сохранена!", reply_markup=main_menu_kb)
    user_context.pop(user_id, None)
    await start(callback.message)
    await callback.answer()

@dp.callback_query(F.data == "view_schedule")
async def view_schedule(callback: types.CallbackQuery):
    await send_user_schedule(callback.message, callback.from_user.id)
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
        await callback.message.answer("Запись не найдена.", reply_markup=main_menu_kb)
        await callback.answer()
        return
    found["status"] = "отменено"
    save_data(data)
    await callback.message.answer(f"✅ Ваша запись {date_s} {time_s} отменена! Все получат уведомление о свободном времени.", reply_markup=main_menu_kb)
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
    await start(callback.message)
    await callback.answer()

# ... ваш остальной код — админ-панель, напоминания, автоподгрузка ...

async def auto_update_code():
    current_file = sys.argv[0]
    last_hash = None
    print("Проверка обновлений с GitHub активна!")
    while True:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(GITHUB_RAW_URL) as resp:
                    if resp.status == 200:
                        remote_code = await resp.text()
                        remote_hash = hash(remote_code)
                        if last_hash is None:
                            last_hash = remote_hash
                        elif remote_hash != last_hash:
                            print("❗Обнаружено обновление кода на GitHub!")
                            with open(current_file, "w", encoding="utf-8") as f:
                                f.write(remote_code)
                            print("Код обновлён. Перезапуск...")
                            os.execv(sys.executable, [sys.executable] + sys.argv)
                            return
        except Exception as e:
            print("Ошибка проверки обновления:", e)
        await asyncio.sleep(60)

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
    print("Бот стартует.")
    asyncio.create_task(send_reminders())
    asyncio.create_task(auto_update_code())
    await dp.start_polling(bot)

if __name__ == "__main__":
    print("=== Новый запуск DRIVE_BOT ===")
    asyncio.run(main())
