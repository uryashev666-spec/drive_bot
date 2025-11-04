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
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
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

def get_main_menu_kb(user_id):
    buttons = [
        [KeyboardButton(text="📅 Моё расписание")],
        [KeyboardButton(text="✏️ Записаться на занятие")],
        [KeyboardButton(text="💬 Написать инструктору")]
    ]
    if user_id == YOUR_TELEGRAM_ID:
        buttons.insert(0, [KeyboardButton(text="🛡️ Админ-панель")])
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

def get_workdays(count=14):
    weekdays_ru = ["Пн", "Вт", "Ср", "Чт", "Пт"]
    today = datetime.today()
    days = []
    current = today + timedelta(days=1)
    while len(days) < count:
        if current.weekday() < 5:
            d = current.strftime("%d.%m.%Y")
            days.append((weekdays_ru[current.weekday()], d))
        current += timedelta(days=1)
    return days

def get_times():
    return ["08:00", "09:20", "10:40", "12:50", "14:10", "15:30"]

def safe_datetime(date_s, time_s):
    try:
        return datetime.strptime(f"{date_s} {time_s}", "%d.%m.%Y %H:%M")
    except Exception:
        return None

def make_two_row_keyboard(button_texts, extras=[]):
    kb = []
    row = []
    for idx, button in enumerate(button_texts):
        row.append(KeyboardButton(text=button))
        if len(row) == 2 or idx == len(button_texts)-1:
            kb.append(row)
            row = []
    for ext in extras:
        kb.append([KeyboardButton(text=ext)])
    return kb

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
    for idx, item in enumerate(my_records):
        text += f"🟢 <b>Моя запись {idx+1}:</b>\n📆 {item['date']}\n🕒 {item['time']}\n📍 {item['address']}\n\n"
    if not text:
        text = "У вас нет записей на ближайшее время."
    await message.answer(text)

@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer(
        "👋 <b>Добро пожаловать!</b>\nЯ, помощник автоинструктора. Для записи пользуйтесь главным меню ⬇️",
        reply_markup=get_main_menu_kb(message.from_user.id)
    )

@dp.message()
async def message_handler(message: types.Message):
    text = message.text.strip()
    user_id = message.from_user.id

    # Навигация: главное меню и назад для любого этапа
    if text == "🏠 Главное меню":
        await message.answer("Главное меню", reply_markup=get_main_menu_kb(user_id))
        user_context.pop(user_id, None)
        return
    if text == "🔙 Назад":
        step = user_context.get(user_id, {}).get("step")
        if step == "choose_time" or step == "choose_address":
            data = load_data()
            days = get_workdays()
            available_days = []
            for name, date in days:
                busy_count = sum(
                    1 for t in get_times()
                    if any(item["date"]==date and item["time"]==t and item.get("status")!="отменено"
                           for item in data["schedule"])
                )
                if busy_count < len(get_times()):
                    available_days.append((name, date))
            days_buttons = [f"📆 {name} {date}" for name, date in available_days]
            kb = make_two_row_keyboard(days_buttons, extras=["🏠 Главное меню"])
            markup = ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
            user_context[user_id]["step"] = "choose_day"
            user_context[user_id]["days"] = [date for _, date in available_days]
            await message.answer("📅 <b>Шаг 1:</b> Выберите день из доступных:", reply_markup=markup)
            return
        if step == "confirm_record":
            kb = make_two_row_keyboard([], extras=["🏠 Главное меню", "🔙 Назад"])
            await message.answer("📍 Введите адрес (куда подъехать):", reply_markup=ReplyKeyboardMarkup(keyboard=kb,resize_keyboard=True))
            user_context[user_id]["step"] = "choose_address"
            return
        await message.answer("Главное меню", reply_markup=get_main_menu_kb(user_id))
        user_context.pop(user_id, None)
        return

    if text == "🛡️ Админ-панель" and user_id == YOUR_TELEGRAM_ID:
        days = get_workdays()
        days_buttons = [f"📆 {name} {date}" for name, date in days]
        kb = make_two_row_keyboard(days_buttons, extras=["🏠 Главное меню"])
        markup = ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
        await message.answer("<b>🛡️ Админ-панель</b>\nВыберите день для управления:", reply_markup=markup)
        user_context[user_id] = {"admin_mode": True, "days": [date for _, date in days], "step": "admin_day"}
        return

    # --- админ-функции как прежде, пропущены ради краткости ---

    if text == "📅 Моё расписание":
        await send_user_schedule(message, user_id)
        return

    if text == "✏️ Записаться на занятие":
        data = load_data()
        days = get_workdays()
        available_days = []
        for name, date in days:
            busy_count = sum(
                1 for t in get_times()
                if any(item["date"]==date and item["time"]==t and item.get("status")!="отменено"
                       for item in data["schedule"])
            )
            if busy_count < len(get_times()):
                available_days.append((name, date))
        days_buttons = [f"📆 {name} {date}" for name, date in available_days]
        kb = make_two_row_keyboard(days_buttons, extras=["🏠 Главное меню"])
        markup = ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
        user_context[user_id] = {"step": "choose_day", "days": [date for _, date in available_days]}
        await message.answer("📅 <b>Шаг 1:</b> Выберите день из доступных:", reply_markup=markup)
        return

    if user_context.get(user_id, {}).get("step") == "choose_day":
        selected_day = None
        for date in user_context[user_id]["days"]:
            if date in text:
                selected_day = date
                break
        if not selected_day:
            await message.answer("Пожалуйста, выберите день из предложенных!")
            return
        times = get_times()
        data = load_data()
        times_buttons = []
        for t in times:
            busy = any(item["date"]==selected_day and item["time"]==t and item.get("status")!="отменено" for item in data["schedule"])
            if busy:
                times_buttons.append(f"🔴 {t} (занято)")
            else:
                times_buttons.append(f"🟢 {t}")
        kb = make_two_row_keyboard(times_buttons, extras=["🏠 Главное меню", "🔙 Назад"])
        markup = ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
        user_context[user_id]["step"] = "choose_time"
        user_context[user_id]["date"] = selected_day
        await message.answer(f"🕒 <b>Шаг 2:</b> Выберите свободное время для {selected_day}:", reply_markup=markup)
        return

    if user_context.get(user_id, {}).get("step") == "choose_time":
        chosen_time = text[-5:]
        if chosen_time not in get_times():
            await message.answer("Пожалуйста, выберите время из предложенных!")
            return
        date_chosen = user_context[user_id]["date"]
        busy = any(item["date"]==date_chosen and item["time"]==chosen_time and item.get("status")!="отменено" for item in load_data()["schedule"])
        if busy:
            await message.answer("Это время уже занято. Выберите другой слот!")
            return
        user_context[user_id]["step"] = "choose_address"
        user_context[user_id]["time"] = chosen_time
        uid_str = str(user_id)
        fio = users_info.get(uid_str, {}).get("fio")
        address = users_info.get(uid_str, {}).get("address")
        if address:
            kb = make_two_row_keyboard([], extras=["🏠 Главное меню", "🔙 Назад", "✅ Оставить адрес"])
            await message.answer(f"📍 <b>Ваш адрес:</b> <u>{address}</u>\nЕсли нужно изменить — напишите новый.\nЕсли подходит — нажмите 'Оставить адрес'.", reply_markup=ReplyKeyboardMarkup(keyboard=kb,resize_keyboard=True))
        else:
            kb = make_two_row_keyboard([], extras=["🏠 Главное меню", "🔙 Назад"])
            await message.answer("📍 <b>Шаг 3:</b> Введите адрес (куда подъехать):", reply_markup=ReplyKeyboardMarkup(keyboard=kb,resize_keyboard=True))
        return

    if user_context.get(user_id, {}).get("step") == "choose_address":
        uid_str = str(user_id)
        if text == "✅ Оставить адрес":
            address = users_info.get(uid_str, {}).get("address")
        else:
            address = text.strip()
            users_info[uid_str] = users_info.get(uid_str, {})
            users_info[uid_str]["address"] = address
            save_users_info(users_info)
        fio = users_info.get(uid_str, {}).get("fio")
        if not fio:
            kb = make_two_row_keyboard([], extras=["🏠 Главное меню", "🔙 Назад"])
            await message.answer("👤 <b>Введите фамилию и имя (пример: Иванов Иван)</b>", reply_markup=ReplyKeyboardMarkup(keyboard=kb,resize_keyboard=True))
            user_context[user_id]["step"] = "choose_fio"
            return
        else:
            user_context[user_id]["address"] = address
            user_context[user_id]["fio"] = fio
            user_context[user_id]["step"] = "confirm_record"
            kb = make_two_row_keyboard([], extras=["✅ Подтвердить запись", "🔙 Назад", "🏠 Главное меню"])
            await send_record_confirmation(message, user_id, kb)
            return

    if user_context.get(user_id, {}).get("step") == "choose_fio":
        fio = text.strip()
        uid_str = str(user_id)
        users_info[uid_str] = users_info.get(uid_str, {})
        users_info[uid_str]["fio"] = fio
        save_users_info(users_info)
        user_context[user_id]["fio"] = fio
        user_context[user_id]["address"] = users_info.get(uid_str, {}).get("address")
        user_context[user_id]["step"] = "confirm_record"
        kb = make_two_row_keyboard([], extras=["✅ Подтвердить запись", "🔙 Назад", "🏠 Главное меню"])
        await send_record_confirmation(message, user_id, kb)
        return

    if user_context.get(user_id, {}).get("step") == "confirm_record":
        if text == "✅ Подтвердить запись":
            ctx = user_context[user_id]
            data = load_data()
            fio_words = ctx.get("fio", "").split()
            surname = fio_words[0] if len(fio_words) >= 1 else ""
            name = fio_words[1] if len(fio_words) >= 2 else ""
            data["schedule"].append({
                "date": ctx["date"],
                "time": ctx["time"],
                "name": name,
                "surname": surname,
                "address": ctx["address"],
                "user_id": user_id
            })
            save_data(data)
            msg = (
                f"✅ <b>Запись подтверждена!</b>\n"
                f"📆 <b>Дата:</b> {ctx['date']}\n"
                f"🕒 <b>Время:</b> {ctx['time']}\n"
                f"👤 <b>ФИО:</b> {ctx['fio']}\n"
                f"📍 <b>Адрес:</b> {ctx['address']}"
            )
            await message.answer(msg, reply_markup=get_main_menu_kb(user_id))
            user_context.pop(user_id, None)
            return

        if text == "🔙 Назад":
            kb = make_two_row_keyboard([], extras=["🏠 Главное меню", "🔙 Назад"])
            await message.answer("📍 Введите адрес (куда подъехать):", reply_markup=ReplyKeyboardMarkup(keyboard=kb,resize_keyboard=True))
            user_context[user_id]["step"] = "choose_address"
            return

        if text == "🏠 Главное меню":
            await message.answer("Главное меню", reply_markup=get_main_menu_kb(user_id))
            user_context.pop(user_id, None)
            return

    if text == "💬 Написать инструктору":
        await message.answer("✉️ Для обращения к инструктору пишите сюда: " + TELEGRAM_LINK)
        return

    await message.answer("⚠️ Неизвестная команда или неправильный формат. Используйте меню.", reply_markup=get_main_menu_kb(user_id))

async def send_record_confirmation(message, user_id, kb):
    ctx = user_context[user_id]
    msg = (
        f"❕ <b>Проверьте все данные!</b>\n"
        f"📆 <b>Дата:</b> {ctx['date']}\n"
        f"🕒 <b>Время:</b> {ctx['time']}\n"
        f"👤 <b>ФИО:</b> {ctx.get('fio','')}\n"
        f"📍 <b>Адрес:</b> {ctx['address']}\n\n"
        f"Если всё правильно — подтвердите!"
    )
    await message.answer(msg, reply_markup=ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True))

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
                        await bot.send_message(item["user_id"], f"🔔 Напоминание: занятие завтра в {item['time']} ({item['date']})")
                    except Exception:
                        pass
                if 0 < (session_time - now).total_seconds() <= 1200:
                    try:
                        await bot.send_message(item["user_id"], f"⏰ Напоминание: занятие через 20 минут!")
                    except Exception:
                        pass
        await asyncio.sleep(60)

async def main():
    print("=== Новый запуск DRIVE_BOT ===")
    asyncio.create_task(send_reminders())
    asyncio.create_task(auto_update_code())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
