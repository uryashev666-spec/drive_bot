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
    days = []
    current = date.today()
    while len(days) < count:
        if current.weekday() < 5:
            day_name = weekdays_ru[current.weekday()]
            days.append((day_name, current.strftime("%d.%m.%Y")))
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
    days = get_workdays(10)
    builder = InlineKeyboardBuilder()
    for day_name, d in days:
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
            builder.button(text=f"❌ {t}", callback_data="busy")  # неактивно
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
    await callback.message.answer("👤 Введите имя и фамилию через пробел (например: Иван Иванов)")
    await state.set_state(Booking.waiting_for_name)
    await callback.answer()

@dp.message(Booking.waiting_for_name)
async def process_name(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    parts = message.text.strip().split()
    if len(parts) < 2:
        await message.answer("Пожалуйста, укажите имя и фамилию через пробел.")
        return
    user_context[user_id]["name"] = parts[0]
    user_context[user_id]["surname"] = " ".join(parts[1:])
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
        f"Имя: {uc['name']}\n"
        f"Фамилия: {uc['surname']}\n"
        f"Адрес: {uc['address']}\n"
        f"Дата: {uc['date']}\n"
        f"Время: {uc['time']}\n"
        "Нажмите кнопку ниже для подтверждения.",
        reply_markup=builder.as_markup()
    )
    await state.clear()

async def remind_later(user_id, date_s, time_s, address):
    dt = datetime.strptime(f"{date_s} {time_s}", "%d.%m.%Y %H:%M")
    delay = (dt - timedelta(minutes=20) - datetime.now()).total_seconds()
    if delay > 0:
        await asyncio.sleep(delay)
        msg = (
            f"⏰ Напоминание!\n"
            f"Занятие через 20 минут.\n"
            f"Дата: {date_s}\n"
            f"Время: {time_s}\n"
            f"Адрес: {address}"
        )
        try:
            await bot.send_message(user_id, msg)
        except Exception:
            pass

@dp.callback_query(F.data == "confirm_entry")
async def confirm_entry(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    user_data = user_context.get(user_id)
    data = load_data()
    if not user_data:
        await callback.message.answer("Ошибка, попробуйте выбрать день заново.")
        await callback.answer()
        return

    date_s = user_data["date"]
    time_s = user_data["time"]
    name = user_data["name"]
    surname = user_data["surname"]
    address = user_data["address"]
    count = len(get_user_week_records(data["schedule"], user_id))

    if count >= 3:
        await callback.message.answer("❌ За одну неделю нельзя записаться более 3 раз.")
        await callback.answer()
        return
    for item in data["schedule"]:
        if item["date"] == date_s and item["time"] == time_s and item.get("status") != "отменено":
            await callback.message.answer("❌ Этот слот уже занят.")
            await callback.answer()
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

    card_text = (
        f"🟢 Новая запись!\n\n"
        f"Имя: {name}\n"
        f"Фамилия: {surname}\n"
        f"Адрес: {address}\n"
        f"Дата: {date_s}\n"
        f"Время: {time_s}"
    )
    await bot.send_message(YOUR_TELEGRAM_ID, card_text)
    msg_user = (
        f"✅ Вы записаны на занятие!\n"
        f"Дата: {date_s}\n"
        f"Время: {time_s}\n"
        f"Адрес: {address}"
    )
    await bot.send_message(user_id, msg_user)
    asyncio.create_task(remind_later(user_id, date_s, time_s, address))
    user_context.pop(user_id, None)
    await callback.answer()

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📅 Расписание", callback_data="view_schedule")],
            [InlineKeyboardButton(text="✏️ Записаться", callback_data="add_record")],
            [InlineKeyboardButton(text="💬 Написать инструктору", url=TELEGRAM_LINK)]
        ]
    )
    await callback.message.answer("✅ Запись подтверждена! Вы возвращены в главное меню.", reply_markup=keyboard)

@dp.callback_query(F.data == "user_cancel")
async def user_cancel(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    data = load_data()
    date_s = user_context[user_id]["date"]
    time_s = user_context[user_id]["time"]
    now = datetime.now()
    dt_slot = datetime.strptime(f"{date_s} {time_s}", "%d.%m.%Y %H:%M")
    hours_left = (dt_slot - now).total_seconds() / 3600
    found = next((item for item in data["schedule"] if
                  item["date"] == date_s and item["time"] == time_s and item["user_id"] == user_id and item.get("status") != "отменено"), None)
    if not found:
        await callback.message.answer("Запись не найдена.")
        await callback.answer()
        return
    if hours_left < 12:
        await callback.message.answer("Отменить занятие через бота поздно (меньше 12 часов). Свяжитесь с инструктором!")
        await callback.answer()
        return

    found["status"] = "отменено"
    save_data(data)
    await callback.message.answer("✅ Запись отменена! Другим пользователям придёт уведомление о свободном времени.")
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

@dp.message(Command("admin"))
async def admin_panel(message: types.Message):
    if message.from_user.id != YOUR_TELEGRAM_ID:
        await message.answer("Нет доступа.")
        return
    data = load_data()
    menu = InlineKeyboardBuilder()
    unique_days = sorted(set(item["date"] for item in data["schedule"]))
    for d in unique_days:
        menu.button(text=d, callback_data=f"admin_day:{d}")
    menu.adjust(1)
    await message.answer("Админ-панель. Выберите день для управления:", reply_markup=menu.as_markup())

@dp.callback_query(F.data.startswith("admin_day:"))
async def admin_day_panel(callback: types.CallbackQuery):
    if callback.from_user.id != YOUR_TELEGRAM_ID:
        await callback.answer()
        return
    chosen_day = callback.data.split(":", 1)[1]
    data = load_data()
    builder = InlineKeyboardBuilder()
    times = sorted(set(item["time"] for item in data["schedule"] if item["date"] == chosen_day))
    for t in times:
        builder.button(text=f"ОТМЕНА {t} с рассылкой", callback_data=f"admin_cancel_time_r:{chosen_day}:{t}")
        builder.button(text=f"ОТМЕНА {t} без рассылки", callback_data=f"admin_cancel_time_n:{chosen_day}:{t}")
    builder.button(text=f"ОТМЕНА весь день", callback_data=f"admin_cancel_day:{chosen_day}")
    builder.adjust(1)
    await callback.message.answer(f"Управление занятиями за {chosen_day}:", reply_markup=builder.as_markup())
    await callback.answer()

@dp.callback_query(F.data.startswith("admin_cancel_day:"))
async def admin_cancel_day(callback: types.CallbackQuery):
    if callback.from_user.id != YOUR_TELEGRAM_ID:
        await callback.answer()
        return
    _, date_s = callback.data.split(":")
    data = load_data()
    affected = [item for item in data["schedule"] if item["date"] == date_s and item.get("status") != "отменено"]
    for item in affected:
        item["status"] = "отменено"
        uid = item.get("user_id")
        try:
            await bot.send_message(uid, "⛔ Ваше занятие отменено, в связи с технической необходимостью.")
        except Exception: pass
    save_data(data)
    await callback.message.answer(f"Все записи на {date_s} отменены. Записаться на этот день нельзя! Уведомление только тем, кто был записан.")
    await callback.answer()

@dp.callback_query(F.data.startswith("admin_cancel_time_r:"))
async def admin_cancel_time_r(callback: types.CallbackQuery):
    _, date_s, time_s = callback.data.split(":")
    data = load_data()
    affected = [item for item in data["schedule"] if item["date"] == date_s and item["time"] == time_s and item.get("status") != "отменено"]
    for item in affected:
        item["status"] = "отменено"
        uid = item.get("user_id")
        try:
            await bot.send_message(uid, f"⛔ Ваше занятие {date_s} {time_s} отменено администратором.")
        except Exception: pass
    save_data(data)
    await callback.message.answer("Выбранный слот отменён. Всем пользователям уведомление о новом свободном времени!")
    for uid in all_users:
        try:
            await bot.send_message(
                uid,
                f"🔔 Освободилось время!\nДата: {date_s}\nВремя: {time_s}\nЗапишитесь, если нужно!"
            )
        except Exception:
            pass
    await callback.answer()

@dp.callback_query(F.data.startswith("admin_cancel_time_n:"))
async def admin_cancel_time_n(callback: types.CallbackQuery):
    _, date_s, time_s = callback.data.split(":")
    data = load_data()
    affected = [item for item in data["schedule"] if item["date"] == date_s and item["time"] == time_s and item.get("status") != "отменено"]
    for item in affected:
        item["status"] = "отменено"
        uid = item.get("user_id")
        try:
            await bot.send_message(uid, f"⛔ Ваше занятие {date_s} {time_s} отменено администратором.")
        except Exception: pass
    save_data(data)
    await callback.message.answer("Слот отменён, уведомление только отменяемому ученику, запись для остальных невозможна.")
    await callback.answer()

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
