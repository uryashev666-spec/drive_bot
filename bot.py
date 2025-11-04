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
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
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

def get_workdays(count=14):
    weekdays_ru = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница"]
    today = datetime.today()
    days = []
    current = today + timedelta(days=1)
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
        text += f"🟢 Моя запись {idx+1}:\nДата: {item['date']}\nВремя: {item['time']}\nАдрес: {item['address']}\n"
    if not text:
        text = "У вас нет записей на ближайшее время."
    await message.answer(text)

@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer(
        "👋 Привет! Я бот автоинструктора. Можешь посмотреть расписание и записаться на занятие.",
        reply_markup=get_main_menu_kb(message.from_user.id)
    )

@dp.message()
async def message_handler(message: types.Message):
    text = message.text.strip()
    user_id = message.from_user.id

    # Админ-панель
    if text == "🛡 Админ-панель" and user_id == YOUR_TELEGRAM_ID:
        days = get_workdays()
        reply = "🛡 Админ-панель: выберите день, чтобы отменить все занятия, либо управлять каждым слотом\n\n"
        for name, date in days:
            reply += f"{name} {date}\n"
        reply += "\nНапишите дату (например: 07.11.2025) или 'отмена день:ДД.ММ.ГГГГ'\n"
        await message.answer(reply)
        user_context[user_id] = {"admin_mode": True, "days": [date for _, date in days]}
        return

    # Отмена всех занятий на день
    if text.startswith("отмена день:") and user_id == YOUR_TELEGRAM_ID:
        day = text.replace("отмена день:", "").strip()
        data = load_data()
        cancelled_users = set()
        for item in data["schedule"]:
            if item["date"] == day and item.get("status") != "отменено":
                item["status"] = "отменено"
                cancelled_users.add(item["user_id"])
        save_data(data)
        for uid in cancelled_users:
            try:
                await bot.send_message(uid, "⛔ Занятие отменено в связи с технической необходимостью")
            except Exception:
                pass
        await message.answer(f"Все занятия на {day} отменены, уведомление отправлено всем.")
        return

    # Управление отдельными слотами (освободить/закрыть)
    if user_context.get(user_id, {}).get("admin_mode") and text in user_context[user_id]["days"]:
        times = get_times()
        data = load_data()
        msg = f"День: {text}\nВыберите время для управления:\n"
        for t in times:
            slot = next((i for i in data["schedule"] if i["date"] == text and i["time"] == t and i.get("status") != "отменено"), None)
            status = slot["status"] if slot else "свободно"
            msg += f"{t}: {'занято' if slot else 'свободно'} ({status})\n"
        msg += "\nДля отмены занятия/освобождения слота напишите: освободить ДД.ММ.ГГГГ ХХ:ММ\n"
        msg += "Для закрытия слота напишите: закрыть ДД.ММ.ГГГГ ХХ:ММ"
        await message.answer(msg)
        user_context[user_id]["admin_day"] = text
        return

    if text.startswith("освободить ") and user_id == YOUR_TELEGRAM_ID:
        rest = text.replace("освободить ", "")
        date_s, time_s = rest.split()
        data = load_data()
        found = next((item for item in data["schedule"] if item["date"]==date_s and item["time"]==time_s and item.get("status")!="отменено"), None)
        if not found:
            await message.answer("Занятие не найдено или уже свободно.")
            return
        found["status"] = "отменено"
        save_data(data)
        all_users = set(x["user_id"] for x in data["schedule"])
        for uid in all_users:
            try:
                await bot.send_message(uid, f"🔔 Освободилось время занятий!\nДата: {date_s}\nВремя: {time_s}\nМожете записаться!")
            except Exception:
                pass
        await message.answer(f"Слот {date_s} {time_s} освобожден, уведомление разослано.")
        return

    if text.startswith("закрыть ") and user_id == YOUR_TELEGRAM_ID:
        rest = text.replace("закрыть ", "")
        date_s, time_s = rest.split()
        data = load_data()
        found = next((item for item in data["schedule"] if item["date"]==date_s and item["time"]==time_s), None)
        if not found:
            fake = {
                "date": date_s,
                "time": time_s,
                "name": "-",
                "surname": "-",
                "address": "-",
                "user_id": -1,
                "status": "заблокировано"
            }
            data["schedule"].append(fake)
        else:
            found["status"] = "заблокировано"
        save_data(data)
        all_users = set(x["user_id"] for x in data["schedule"])
        for uid in all_users:
            try:
                await bot.send_message(uid, f"⛔ Cлот {date_s} {time_s} закрыт для записи (тех. причина / админ блок).")
            except Exception:
                pass
        await message.answer(f"Слот {date_s} {time_s} закрыт для записи, уведомление разослано.")
        return

    # Моё расписание
    if text == "📅 Моё расписание":
        await send_user_schedule(message, user_id)
        return

    # Начало записи на занятие: выбор дня
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
        kb_days = [[KeyboardButton(text=f"{name} {date}")] for name, date in available_days]
        markup = ReplyKeyboardMarkup(keyboard=kb_days, resize_keyboard=True)
        user_context[user_id] = {"step": "choose_day", "days": [date for _, date in available_days]}
        await message.answer("📅 Выберите день для занятия из свободных (две недели вперед, только рабочие дни):",
                            reply_markup=markup)
        return

    # Выбор времени (reply-слоты)
    if user_context.get(user_id, {}).get("step") == "choose_day":
        # user отправил дату, находим текстовое совпадение с кнопкой
        selected_day = None
        for date in user_context[user_id]["days"]:
            if date in text:
                selected_day = date
                break
        if not selected_day:
            await message.answer("Пожалуйста, выберите день из предложенных кнопок.")
            return
        times = get_times()
        data = load_data()
        kb_times = []
        for t in times:
            busy = any(item["date"]==selected_day and item["time"]==t and item.get("status")!="отменено" for item in data["schedule"])
            label = f"{t} {'🚫' if busy else ''}"
            kb_times.append([KeyboardButton(text=label if not busy else f"{t} (занято)")])
        markup = ReplyKeyboardMarkup(keyboard=kb_times, resize_keyboard=True)
        user_context[user_id]["step"] = "choose_time"
        user_context[user_id]["date"] = selected_day
        await message.answer(f"Выберите время для занятия {selected_day}:", reply_markup=markup)
        return

    # Получение выбора времени
    if user_context.get(user_id, {}).get("step") == "choose_time":
        chosen_time = text.split()[0].strip()
        if chosen_time not in get_times():
            await message.answer("Пожалуйста, выберите время из предложенных слотов.")
            return
        date_chosen = user_context[user_id]["date"]
        busy = any(item["date"]==date_chosen and item["time"]==chosen_time and item.get("status")!="отменено" for item in load_data()["schedule"])
        if busy:
            await message.answer("Это время уже занято. Выберите другой свободный слот.")
            return
        user_context[user_id]["step"] = "write_fio"
        user_context[user_id]["time"] = chosen_time
        await message.answer("👤 Введите фамилию и имя через пробел (например: Иванов Иван)", reply_markup=get_main_menu_kb(user_id))
        return

    # Получение ФИО
    if user_context.get(user_id, {}).get("step") == "write_fio":
        parts = text.strip().split(" ", 1)
        if len(parts) < 2:
            await message.answer("Пожалуйста, напишите фамилию и имя через пробел.")
            return
        user_context[user_id]["surname"], user_context[user_id]["name"] = parts[0], parts[1]
        await message.answer("📍 Введите адрес, куда подъехать:")
        user_context[user_id]["step"] = "write_address"
        return

    if user_context.get(user_id, {}).get("step") == "write_address":
        ctx = user_context[user_id]
        ctx["address"] = text.strip()
        # сохраняем запись
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
        await message.answer(f"✅ Запись подтверждена: {ctx['date']}, {ctx['time']}, {ctx['surname']} {ctx['name']}, адрес: {ctx['address']}")
        user_context.pop(user_id, None)
        return

    if text == "💬 Написать инструктору":
        await message.answer("Вы можете написать инструктору: " + TELEGRAM_LINK)
        return

    await message.answer("Неизвестная команда или неправильный формат данных. Пожалуйста, используйте меню.")

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
