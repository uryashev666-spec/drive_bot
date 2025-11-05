import asyncio
import json
import logging
import os
import sys
import aiohttp
import re
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types
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

def match_btn(text, variant):
    return text.strip().lower().endswith(variant.strip().lower())

def extract_date_from_btn(text):
    match = re.search(r"\d{2}\.\d{2}\.\d{4}", text)
    return match.group(0) if match else None

def extract_time_from_btn(text):
    match = re.search(r"\d{2}:\d{2}", text)
    return match.group(0) if match else None

def get_main_menu_kb(user_id):
    buttons = [
        [KeyboardButton(text="📅 Моё расписание")],
        [KeyboardButton(text="✏️ Записаться на занятие")],
        [KeyboardButton(text="💬 Написать инструктору")]
    ]
    if user_id == YOUR_TELEGRAM_ID:
        buttons.insert(0, [KeyboardButton(text="🛡️ Админ-панель")])
    return ReplyKeyboardMarkup(
        keyboard=buttons, resize_keyboard=True, one_time_keyboard=False
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

def get_user_records(user_id):
    data = load_data()
    return [item for item in data["schedule"]
            if item.get("user_id") == user_id and item.get("status") != "отменено"]

def week_limit(user_id, target_date):
    user_records = get_user_records(user_id)
    new_dt = datetime.strptime(target_date, "%d.%m.%Y")
    week_dates = [(new_dt + timedelta(days=i)).strftime("%d.%m.%Y") for i in range(-6, 1)]
    return sum(1 for item in user_records if item.get("date") in week_dates)

def has_day_record(user_id, date):
    user_records = get_user_records(user_id)
    return any(item.get("date") == date for item in user_records)

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
    buttons = []
    for idx, item in enumerate(my_records):
        time_left = (safe_datetime(item['date'], item['time']) - now).total_seconds()
        text += f"🟢 <b>Моя запись {idx+1}:</b>\n📆 {item['date']}\n🕒 {item['time']}\n📍 {item['address']}\n"
        if time_left > 0:
            label = f"❌ Отменить {item['date']} {item['time']}"
            buttons.append([KeyboardButton(text=label)])
        text += "\n"
    if not text:
        text = "У вас нет записей на ближайшее время."
    markup = ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True) if buttons else None
    await message.answer(text, reply_markup=markup if markup else None)

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

    if match_btn(text, "Главное меню"):
        await message.answer("Главное меню", reply_markup=get_main_menu_kb(user_id))
        user_context.pop(user_id, None)
        return

    if text.startswith("❌ Отменить"):
        parts = text.replace("❌ Отменить", "").strip().split()
        if len(parts) != 2:
            await message.answer("Ошибка формата! Попробуйте отмену снова из расписания.", reply_markup=get_main_menu_kb(user_id))
            return
        date_s, time_s = parts
        data = load_data()
        record = next((item for item in data["schedule"] if item["date"]==date_s and item["time"]==time_s and item.get("user_id")==user_id and item.get("status")!="отменено"), None)
        if not record:
            await message.answer("Запись не найдена или уже отменена.", reply_markup=get_main_menu_kb(user_id))
            return
        dt = safe_datetime(date_s, time_s)
        now = datetime.now()
        if (dt - now).total_seconds() < 0:
            await message.answer("Эта запись в прошлом.", reply_markup=get_main_menu_kb(user_id))
            return
        if (dt - now).total_seconds() < 12*3600:
            await message.answer(
                "Отмена этого занятия менее чем за 12 часов невозможна через бота. "
                f"Если у вас изменились планы, срочно напишите инструктору лично: {TELEGRAM_LINK}",
                reply_markup=get_main_menu_kb(user_id)
            )
            return
        record["status"] = "отменено"
        save_data(data)
        users_to_notify = set(item["user_id"] for item in data["schedule"]) | {YOUR_TELEGRAM_ID}
        for uid in users_to_notify:
            if uid != user_id:
                try:
                    await bot.send_message(uid, f"🔔 Освободился слот!\nДата: {date_s}, время: {time_s}. Можно записаться через меню.")
                except Exception:
                    pass
        await message.answer(f"✅ Занятие {date_s} {time_s} отменено и доступно для других учеников.", reply_markup=get_main_menu_kb(user_id))
        return

    # --- ADMIN PANEL ---
    if user_id == YOUR_TELEGRAM_ID and match_btn(text, "Админ-панель"):
        days = get_workdays()
        days_buttons = [f"📆 {name} {date}" for name, date in days]
        kb = make_two_row_keyboard(days_buttons, extras=["🏠 Главное меню"])
        markup = ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
        user_context[user_id] = {"admin_mode": True, "admin_step": "admin_day", "days": [date for _, date in days]}
        await message.answer("<b>🛡️ Админ-панель</b>\nВыберите день для управления:", reply_markup=markup)
        return

    if user_context.get(user_id, {}).get("admin_mode") and user_context[user_id].get("admin_step") == "admin_day":
        btn_date = extract_date_from_btn(text)
        if btn_date and btn_date in user_context[user_id]["days"]:
            selected_date = btn_date
            times = get_times()
            data = load_data()
            slot_buttons = []
            for t in times:
                slot = next((i for i in data["schedule"] if i["date"] == selected_date and i["time"] == t and i.get("status") != "отменено"), None)
                if slot and slot.get("status") == "заблокировано":
                    slot_buttons.append(f"⛔ {t}")
                elif slot:
                    slot_buttons.append(f"🔴 {t}")
                else:
                    slot_buttons.append(f"🟢 {t}")
            slot_buttons.append("❗ Отменить все занятия на день")
            kb = make_two_row_keyboard(slot_buttons, extras=["🏠 Главное меню", "🔙 Назад"])
            markup = ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
            user_context[user_id].update({"admin_step": "admin_time", "admin_day": selected_date, "times": times})
            await message.answer(
                f"День {selected_date}: выберите слот или отмените весь день.",
                reply_markup=markup
            )
            return
        else:
            await message.answer("Пожалуйста, выберите день из предложенных кнопок.", reply_markup=ReplyKeyboardMarkup(
                keyboard=[[KeyboardButton(text=f"📆 {name} {date}") for name, date in get_workdays()]],
                resize_keyboard=True
            ))
            return

    # --- USER choose_day: по дате из кнопки ---
    if user_context.get(user_id, {}).get("step") == "choose_day":
        btn_date = extract_date_from_btn(text)
        if btn_date and btn_date in user_context[user_id]["days"]:
            selected_day = btn_date
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
            await message.answer(f"🕒 <b>Шаг 2:</b> Выберите время для {selected_day}:", reply_markup=markup)
            return
        else:
            await message.answer("Пожалуйста, выберите день из кнопок.", reply_markup=ReplyKeyboardMarkup(
                keyboard=[[KeyboardButton(text=f"📆 {name} {date}") for name, date in get_workdays()]],
                resize_keyboard=True
            ))
            return

    # --- USER choose_time: универсальный ---
    if user_context.get(user_id, {}).get("step") == "choose_time":
        chosen_time = extract_time_from_btn(text)
        if not chosen_time or chosen_time not in get_times():
            await message.answer("Пожалуйста, выберите время из кнопок.", reply_markup=ReplyKeyboardMarkup(
                keyboard=[[KeyboardButton(text=f"🟢 {t}") for t in get_times()]],
                resize_keyboard=True
            ))
            return
        # Далее обычный шаг: лимиты, проверка свободно/занято, ввод ФИО/адреса, подтверждение
        # Пример, реализуй workflow как раньше:

        selected_day = user_context[user_id]["date"]
        busy = any(item["date"]==selected_day and item["time"]==chosen_time and item.get("status")!="отменено" for item in load_data()["schedule"])
        if busy:
            await message.answer("Это время уже занято. Выберите другой слот!", reply_markup=get_main_menu_kb(user_id))
            return

        user_context[user_id]["step"] = "choose_fio"
        user_context[user_id]["time"] = chosen_time
        uid_str = str(user_id)
        fio = users_info.get(uid_str, {}).get("fio")
        address = users_info.get(uid_str, {}).get("address")
        if fio:
            user_context[user_id]["fio"] = fio
            user_context[user_id]["step"] = "choose_address"
            if address:
                kb = make_two_row_keyboard([], extras=["🏠 Главное меню", "🔙 Назад", "✅ Оставить адрес"])
                await message.answer(f"📍 <b>Ваш адрес:</b> <u>{address}</u>\nЕсли нужно изменить — напишите новый.\nЕсли подходит — нажмите 'Оставить адрес'.", reply_markup=ReplyKeyboardMarkup(keyboard=kb,resize_keyboard=True))
            else:
                kb = make_two_row_keyboard([], extras=["🏠 Главное меню", "🔙 Назад"])
                await message.answer("📍 Введите адрес (куда подъехать):", reply_markup=ReplyKeyboardMarkup(keyboard=kb,resize_keyboard=True))
            return
        else:
            kb = make_two_row_keyboard([], extras=["🏠 Главное меню", "🔙 Назад"])
            await message.answer("👤 Введите фамилию и имя (пример: Иванов Иван):", reply_markup=ReplyKeyboardMarkup(keyboard=kb,resize_keyboard=True))
            return

    # --- USER: этап ввода ФИО ---
    if user_context.get(user_id, {}).get("step") == "choose_fio":
        fio = text.strip()
        uid_str = str(user_id)
        users_info[uid_str] = users_info.get(uid_str, {})
        users_info[uid_str]["fio"] = fio
        save_users_info(users_info)
        user_context[user_id]["fio"] = fio
        user_context[user_id]["step"] = "choose_address"
        address = users_info.get(uid_str, {}).get("address")
        if address:
            kb = make_two_row_keyboard([], extras=["🏠 Главное меню", "🔙 Назад", "✅ Оставить адрес"])
            await message.answer(f"📍 <b>Ваш адрес:</b> <u>{address}</u>\nЕсли нужно изменить — напишите новый.\nЕсли подходит — нажмите 'Оставить адрес'.", reply_markup=ReplyKeyboardMarkup(keyboard=kb,resize_keyboard=True))
        else:
            kb = make_two_row_keyboard([], extras=["🏠 Главное меню", "🔙 Назад"])
            await message.answer("📍 Введите адрес (куда подъехать):", reply_markup=ReplyKeyboardMarkup(keyboard=kb,resize_keyboard=True))
        return

    # --- USER: этап адрес ---
    if user_context.get(user_id, {}).get("step") == "choose_address":
        uid_str = str(user_id)
        if text == "✅ Оставить адрес":
            address = users_info.get(uid_str, {}).get("address")
        else:
            address = text.strip()
            users_info[uid_str] = users_info.get(uid_str, {})
            users_info[uid_str]["address"] = address
            save_users_info(users_info)
        user_context[user_id]["address"] = address
        user_context[user_id]["step"] = "confirm_record"
        kb = make_two_row_keyboard([], extras=["✅ Подтвердить запись", "🔙 Назад", "🏠 Главное меню"])
        await send_record_confirmation(message, user_id, kb)
        return

    # --- USER: финальное подтверждение ---
    if user_context.get(user_id, {}).get("step") == "confirm_record":
        if text == "✅ Подтвердить запись":
            ctx = user_context[user_id]
            fio_words = ctx.get("fio", "").split()
            surname = fio_words[0] if len(fio_words) >= 1 else ""
            name = fio_words[1] if len(fio_words) >= 2 else ""
            data = load_data()
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
            await bot.send_message(YOUR_TELEGRAM_ID, msg, parse_mode="HTML")
            user_context.pop(user_id, None)
            return

    if match_btn(text, "Моё расписание"):
        await send_user_schedule(message, user_id)
        return

    if match_btn(text, "Записаться на занятие"):
        data = load_data()
        days = get_workdays()
        available_days = []
        days_buttons = []
        for name, date in days:
            if has_day_record(user_id, date):
                days_buttons.append(f"❌ {name} {date} (уже записаны)")
            elif week_limit(user_id, date) >= 2:
                days_buttons.append(f"🚫 {name} {date} (лимит)")
            else:
                days_buttons.append(f"📆 {name} {date}")
                available_days.append((name, date))
        if not available_days:
            await message.answer("Нет доступных дней для записи.", reply_markup=get_main_menu_kb(user_id))
            return
        kb = make_two_row_keyboard(days_buttons, extras=["🏠 Главное меню"])
        markup = ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
        user_context[user_id] = {"step": "choose_day", "days": [date for _, date in available_days]}
        await message.answer(
            "📅 <b>Шаг 1:</b> Выберите день для занятия. Слоты с ❌ или 🚫 недоступны для записи.",
            reply_markup=markup
        )
        return

    if match_btn(text, "Написать инструктору"):
        await message.answer("✉️ Для обращения к инструктору пишите сюда: " + TELEGRAM_LINK)
        return

    await message.answer("⚠️ Неизвестная команда или неправильный формат. Используйте меню.", reply_markup=get_main_menu_kb(user_id))

async def auto_update_code():
    pass

async def send_reminders():
    pass

async def main():
    print("=== Новый запуск DRIVE_BOT ===")
    asyncio.create_task(send_reminders())
    asyncio.create_task(auto_update_code())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
