import asyncio
import json
import logging
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types, F
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command

TOKEN = "7818982442:AAGY-DDMsuvhLg0-Ec1ds43SkAmCltR88cI"
DATA_FILE = "data.json"
TELEGRAM_LINK = "https://t.me/sv010ch"
YOUR_TELEGRAM_ID = 487289287

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
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
    buttons = [
        [InlineKeyboardButton(text="📅 Расписание", callback_data="view_schedule")],
        [InlineKeyboardButton(text="✏️ Записаться", callback_data="add_record")],
        [InlineKeyboardButton(text="💬 Написать инструктору", url=TELEGRAM_LINK)]
    ]
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

@dp.message(Command("admin"))
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
    found = next((item for item in data["schedule"]
                  if item["date"]==date_s and item["time"]==time_s and str(item["user_id"])==str(target_id) and item.get("status")!="отменено"), None)
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

@dp.callback_query(F.data == "view_schedule")
async def view_schedule(callback: types.CallbackQuery):
    data = load_data()
    if not data["schedule"]:
        await callback.message.answer("📭 Расписание пока пустое.")
    else:
        text = "\n".join([
            f'• {item["date"]}, {item["time"]}, {item.get("name", "")} {item.get("surname", "")}, {item.get("address", "")}' 
            + (" [Отмена]" if item.get("status") == "отменено" else "")
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
                item["date"] == date_s
                and item["time"] == time_s
                and item["name"] == name
                and item["surname"] == surname
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
