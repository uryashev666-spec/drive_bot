import asyncio
import json
import logging
from datetime import datetime, timedelta, date
from aiogram import Bot, Dispatcher, types, F
from aiogram.enums import ParseMode
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder

TOKEN = "7818982442:AAGY-DDMsuvhLg0-Ec1ds43SkAmCltR88cI"
DATA_FILE = "data.json"
TELEGRAM_LINK = "https://t.me/sv010ch"
logging.basicConfig(level=logging.INFO)

bot = Bot(token=TOKEN)
dp = Dispatcher()
user_context = {}  # user_id -> {"date": ..., "time": ...}

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
                date_obj = datetime.strptime(item.get("date"), "%d.%m.%Y")
                if 0 <= (now - date_obj).days < 7:
                    result.append(item)
            except Exception:
                continue
    return result

def get_next_weekdays(count=10):
    weekdays_ru = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница"]
    days = []
    current = date.today() + timedelta(days=1)
    while len(days) < count:
        if current.weekday() < 5:
            day_name = weekdays_ru[current.weekday()]
            days.append(f"{day_name}, {current.strftime('%d.%m.%Y')}")
        current += timedelta(days=1)
    return days

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
    days = get_next_weekdays(10)
    keyboard = InlineKeyboardBuilder()
    for day in days:
        keyboard.button(text=day, callback_data=f"select_day:{day}")
    keyboard.adjust(1)
    await callback.message.answer("📅 Выбери день для записи:", reply_markup=keyboard.as_markup())
    await callback.answer()

@dp.callback_query(F.data.startswith("select_day:"))
async def handle_day_selection(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    selected_day = callback.data.split(":", 1)[1]
    user_context[user_id] = {"date": selected_day}

    times = ["8:00", "9:20", "10:40", "12:50", "14:10", "15:30"]
    keyboard = InlineKeyboardBuilder()
    for t in times:
        keyboard.button(text=t, callback_data=f"select_time:{t}")
    keyboard.adjust(2)
    await callback.message.answer(f"🕒 Выбран день: {selected_day}\nТеперь выбери время:", reply_markup=keyboard.as_markup())
    await callback.answer()

@dp.callback_query(F.data.startswith("select_time:"))
async def handle_time_selection(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    selected_time = callback.data.split(":", 1)[1]
    if user_id not in user_context:
        await callback.message.answer("⚠️ Сначала выбери день.")
        await callback.answer()
        return
    user_context[user_id]["time"] = selected_time

    async def final_step(message: types.Message):
        await unregister_save_record(user_id)
        data = load_data()
        try:
            parts = [s.strip() for s in message.text.split(',', 2)]
            if len(parts) != 3:
                raise ValueError("Недостаточно данных")
            name, surname, address = parts
            date_s = user_context[user_id]["date"].split(", ")[1]
            time_s = user_context[user_id]["time"]

            count = len(get_user_week_records(data["schedule"], user_id))
            if count >= 2:
                await message.answer("❌ За одну неделю нельзя записаться более 2 раз.")
                return

            for item in data["schedule"]:
                if item["date"] == date_s and item["time"] == time_s and item.get("status") != "отменено":
                    await message.answer("❌ Этот слот уже занят. Выбери другое время.")
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
        except ValueError as ve:
            await message.answer(f"❗ {ve}")
        except Exception:
            await message.answer("❗ Формат некорректен. Попробуй ещё раз по примеру.")

    dp.message.register(final_step, F.from_user.id == user_id)
    await callback.message.answer("👤 Введи имя, фамилию и адрес (пример: Иван, Иванов, ул. Ленина 5)")
    await callback.answer()

async def unregister_save_record(user_id):
    # безопасно снимаем все зарегистрированные обработчики сообщений для пользователя
    try:
        dp.message.unregister_all(F.from_user.id == user_id)
    except Exception:
        logging.exception("Ошибка при снятии обработчиков сообщений")
    user_context.pop(user_id, None)

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
            except Exception:
                logging.exception(f"Не удалось отправить сообщение пользователю {user_id}")
        found["status"] = "отменено"
        save_data(data)
        await message.answer("⛔ Сообщение об отмене отправлено ученику. Слот останется занятым.")
    except ValueError as ve:
        await message.answer(f"❗ {ve}")
    except Exception:
        await message.answer("❗ Некорректная команда. Пример: /cancel 12.10.2025 14:00 Иван Иванов")

@dp.message(Command("day"))
async def view_day_records(message: types.Message):
    try:
        parts = message.text.split(" ", 1)
        if len(parts) != 2:
            raise ValueError("Неверный формат")
        date_s = parts[1].strip()
        # проверка формата даты (DD.MM.YYYY)
        datetime.strptime(date_s, "%d.%m.%Y")

        data = load_data()
        records = [item for item in data["schedule"] if item["date"] == date_s]
        if not records:
            await message.answer(f"📭 На {date_s} записей нет.")
            return

        text = "\n".join([
            f'• {item["time"]}, {item.get("name", "")} {item.get("surname", "")}, {item.get("address", "")}' +
            (" [Отмена]" if item.get("status") == "отменено" else "")
            for item in records
        ])
        await message.answer(f"📅 Записи на {date_s}:\n\n{text}")
    except ValueError:
        await message.answer("❗ Используй формат: /day 12.10.2025")
    except Exception:
        await message.answer("❗ Произошла ошибка при получении записей. Попробуй ещё раз.")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
