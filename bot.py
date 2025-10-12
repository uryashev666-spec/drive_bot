import asyncio
import json
import logging
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types, F
from aiogram.enums import ParseMode
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command

TOKEN = "7818982442:AAGY-DDMsuvhLg0-Ec1ds43SkAmCltR88cI"
DATA_FILE = "data.json"
TELEGRAM_LINK = "https://t.me/sv010ch"
logging.basicConfig(level=logging.INFO)

bot = Bot(token=TOKEN)
dp = Dispatcher()
user_message_handlers = {}

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
    result = []
    now = datetime.now()
    for item in schedule:
        if item.get("user_id") == user_id:
            try:
                date = datetime.strptime(item.get("date"), "%d.%m.%Y")
                if 0 <= (now - date).days < 7:
                    result.append(item)
            except Exception:
                pass
    return result

def get_save_record_handler(user_id):
    if user_id not in user_message_handlers:
        async def specific_save_record(message: types.Message):
            await save_record_logic(message, user_id)
        user_message_handlers[user_id] = specific_save_record
    return user_message_handlers[user_id]

async def unregister_save_record(user_id):
    handler = user_message_handlers.get(user_id)
    if handler:
        dp.message.unregister(handler, F.from_user.id == user_id)
        del user_message_handlers[user_id]

@dp.message(Command("start"))
async def start(message: types.Message):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📅 Расписание", callback_data="view_schedule")],
            [InlineKeyboardButton(text="✏️ Записаться", callback_data="add_record")],
            [InlineKeyboardButton(text="💬 Написать инструктору", url=TELEGRAM_LINK)]
        ]
    )
    await message.answer(
        "👋 Привет! Я бот автоинструктора. Здесь ты можешь посмотреть расписание и записаться на занятие.",
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML
    )

@dp.callback_query(F.data == "view_schedule")
async def view_schedule(callback: types.CallbackQuery):
    data = load_data()
    if not data["schedule"]:
        await callback.message.answer("📭 Расписание пока пустое.")
    else:
        text = "\n".join([
            f'• {item["date"]}, {item["time"]}, {item.get("name", "")} {item.get("surname", "")}, {item.get("address", "")}' +
            (" [Отмена]" if item.get("status") == "отменено" else "")
            for item in data["schedule"]
        ])
        await callback.message.answer(f"📅 Текущее расписание:\n\n{text}")
    await callback.answer()

@dp.callback_query(F.data == "add_record")
async def add_record(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    handler = get_save_record_handler(user_id)
    dp.message.register(handler, F.from_user.id == user_id)
    await callback.message.answer(
        "✏️ Введи дату, время, имя, фамилию и адрес (пример: 12.10.2025, 14:00, Иван, Иванов, ул. Ленина 5):"
    )
    await callback.answer()

async def save_record_logic(message: types.Message, user_id):
    await unregister_save_record(user_id)
    data = load_data()
    try:
        parts = [s.strip() for s in message.text.split(',', 4)]
        if len(parts) != 5:
            raise ValueError("Недостаточно данных")
        date_s, time_s, name, surname, address = parts
        count = len(get_user_week_records(data["schedule"], user_id))
        if count >= 2:
            await message.answer("❌ За одну неделю нельзя записаться более 2 раз.")
            return
        data["schedule"].append({
            "date": date_s,
            "time": time_s,
            "name": name,
            "surname": surname,
            "address": address,
            "user_id": user_id
        })
        save_data(data)
        await message.answer("✅ Запись добавлена в расписание!")
    except Exception:
        await message.answer("❗ Формат некорректен. Попробуй ещё раз по примеру.")

@dp.message(Command("cancel"))
async def cancel(message: types.Message):
    data = load_data()
    try:
        parts = message.text.split(' ', 4)
        if len(parts) != 5:
            raise ValueError("Некорректное количество аргументов")
        _, date_s, time_s, name, surname = parts
        found = None
        for item in data["schedule"]:
            if (
                item["date"] == date_s and
                item["time"] == time_s and
                item["name"] == name and
                item["surname"] == surname
            ):
                found = item
                break
        if not found:
            await message.answer("❌ Запись не найдена.")
            return
        user_id = found.get("user_id")
        if user_id is not None:
            try:
                await bot.send_message(
                    user_id,
                    "⚠️ Занятие отменено инструктором в связи с технической необходимостью."
                )
            except Exception as e:
                logging.error(f"Could not send cancellation message to user {user_id}: {e}")
        found["status"] = "отменено"
        save_data(data)
        await message.answer("⛔ Сообщение об отмене отправлено ученику. Слот останется занятым.")
    except Exception:
        await message.answer("❗ Некорректная команда. Пример: /cancel 12.10.2025 14:00 Иван Иванов")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
