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
def build_main_menu(user_id: int) -> ReplyKeyboardMarkup:
    keyboard = [
        [KeyboardButton(text="📅 Моё расписание")],
        [KeyboardButton(text="✏️ Записаться")],
        [KeyboardButton(text="💬 Инструктор")]
    ]
    if user_id == YOUR_TELEGRAM_ID:
        keyboard.insert(0, [KeyboardButton(text="🛡 Админ-панель")])
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True, one_time_keyboard=False)

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
    # Убираем inline-кнопки отмены из расписания
    for idx, item in enumerate(my_records):
        text += f"🟢 Моя запись {idx+1}:\nДата: {item['date']}\nВремя: {item['time']}\nАдрес: {item['address']}\n"
    if not text:
        text = "У вас нет записей на ближайшее время."
    await message.answer(text)

async def start_add_record_flow(message: types.Message):
    user_id = message.from_user.id
    user_context[user_id] = {}
    data = load_data()
    # Убираем inline-кнопки выбора дня: выводим список и просим ввести дату вручную
    available = []
    for day_name, day_date in get_workdays(10):
        week_count = week_limit(user_id, day_date)
        if week_count >= 2:
            status = "(лимит)"
        else:
            busy = any(item["date"] == day_date and item["user_id"] == user_id and item.get("status") != "отменено" for item in data["schedule"])
            status = "(занято вами)" if busy else ""
        available.append(f"- {day_name}, {day_date} {status}".strip())
    await message.answer("📅 Доступные дни:\n" + "\n".join(available) + "\n\nОтправьте дату в формате ДД.ММ.ГГГГ")

@dp.message(Command("start"))
async def start(message: types.Message):
    # Показываем только ReplyKeyboard, без inline-кнопок
    await message.answer(
        "👋 Привет! Я бот автоинструктора. Можешь посмотреть расписание и записаться на занятие.",
        reply_markup=build_main_menu(message.from_user.id)
    )

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
    elif text == "🛡 Админ-панель" and message.from_user.id == YOUR_TELEGRAM_ID:
        # Хук для админ-панели (добавьте нужную логику)
        await message.answer("🔧 Админ-панель: команды администратора доступны здесь.")
        return
    await process_name_or_address(message)

# Удаляем все callback_query и inline-ветки, заменяем на диалоговый ввод
# Далее оставшаяся бизнес-логика сохранена, но без inline-подтверждений

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
        # Сохраняем адрес для будущих записей
        info = users_info.get(str(user_id), {})
        info["surname"] = ctx["surname"]
        info["name"] = ctx["name"]
        info["address"] = ctx["address"]
        users_info[str(user_id)] = info
        save_users_info(users_info)
        await message.answer(
            f"Записать на {ctx['date']} {ctx['time']}\nФИО: {ctx['surname']} {ctx['name']}\nАдрес: {ctx['address']}\nНапишите 'подтвердить' для сохранения или 'отмена' для отмены."
        )
        return
    # Обработка подтверждения/отмены
    if text := message.text.strip().lower():
        if text == "подтвердить" and all(k in ctx for k in ("date", "time", "name", "surname", "address")):
            week_count = week_limit(user_id, ctx["date"])
            if week_count >= 2:
                await message.answer("Лимит: не более двух занятий для ученика за семь дней подряд.")
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
                f"🚗 Новая запись!\n"
                f"Дата: {ctx['date']}\n"
                f"Время: {ctx['time']}\n"
                f"ФИО: {ctx['surname']} {ctx['name']}\n"
                f"Адрес: {ctx['address']}"
            )
            try:
                await bot.send_message(YOUR_TELEGRAM_ID, card_text, parse_mode="HTML")
            except Exception:
                pass
            await message.answer("✅ Запись подтверждена и сохранена!")
            user_context.pop(user_id, None)
            await start(message)
            return
        if text == "отмена":
            user_context.pop(user_id, None)
            await message.answer("❌ Запись отменена.")
            return

# Автообновление и напоминания остаются без изменений
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
