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
        [KeyboardButton(text="рџ“… РњРѕС‘ СЂР°СЃРїРёСЃР°РЅРёРµ")],
        [KeyboardButton(text="вњЏпёЏ Р—Р°РїРёСЃР°С‚СЊСЃСЏ РЅР° Р·Р°РЅСЏС‚РёРµ")],
        [KeyboardButton(text="рџ’¬ РќР°РїРёСЃР°С‚СЊ РёРЅСЃС‚СЂСѓРєС‚РѕСЂСѓ")]
    ]
    if user_id == YOUR_TELEGRAM_ID:
        buttons.insert(0, [KeyboardButton(text="рџ›ЎпёЏ РђРґРјРёРЅ-РїР°РЅРµР»СЊ")])
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
    weekdays_ru = ["РџРЅ", "Р’С‚", "РЎСЂ", "Р§С‚", "РџС‚"]
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
            if item.get("user_id") == user_id and item.get("status") != "РѕС‚РјРµРЅРµРЅРѕ"]

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
        if item.get("user_id") == user_id and item.get("status") != "РѕС‚РјРµРЅРµРЅРѕ"
        and safe_datetime(item['date'], item['time']) and safe_datetime(item['date'], item['time']) > now
    ]
    my_records.sort(key=lambda item: safe_datetime(item['date'], item['time']) or datetime.max)
    text = ""
    buttons = []
    for idx, item in enumerate(my_records):
        time_left = (safe_datetime(item['date'], item['time']) - now).total_seconds()
        text += f"рџџў РњРѕСЏ Р·Р°РїРёСЃСЊ {idx+1}:\nрџ“† {item['date']}\nрџ•’ {item['time']}\nрџ“Ќ {item['address']}\n"
        if time_left > 0:
            label = f"вќЊ РћС‚РјРµРЅРёС‚СЊ {item['date']} {item['time']}"
            buttons.append([KeyboardButton(text=label)])
        text += "\n"
    if not text:
        text = "РЈ РІР°СЃ РЅРµС‚ Р·Р°РїРёСЃРµР№ РЅР° Р±Р»РёР¶Р°Р№С€РµРµ РІСЂРµРјСЏ."
    markup = ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True) if buttons else None
    await message.answer(text, reply_markup=markup if markup else None)

async def send_record_confirmation(message, user_id, kb):
    ctx = user_context[user_id]
    msg = (
        f"вќ• РџСЂРѕРІРµСЂСЊС‚Рµ РІСЃРµ РґР°РЅРЅС‹Рµ!\n"
        f"рџ“† Р”Р°С‚Р°: {ctx['date']}\n"
        f"рџ•’ Р’СЂРµРјСЏ: {ctx['time']}\n"
        f"рџ‘¤ Р¤РРћ: {ctx.get('fio','')}\n"
        f"рџ“Ќ РђРґСЂРµСЃ: {ctx['address']}\n\n"
        f"Р•СЃР»Рё РІСЃС‘ РїСЂР°РІРёР»СЊРЅРѕ вЂ” РїРѕРґС‚РІРµСЂРґРёС‚Рµ!"
    )
    await message.answer(msg, reply_markup=ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True))

@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer(
        "рџ‘‹ Р”РѕР±СЂРѕ РїРѕР¶Р°Р»РѕРІР°С‚СЊ!\nРЇ, РїРѕРјРѕС‰РЅРёРє Р°РІС‚РѕРёРЅСЃС‚СЂСѓРєС‚РѕСЂР°. Р”Р»СЏ Р·Р°РїРёСЃРё РїРѕР»СЊР·СѓР№С‚РµСЃСЊ РіР»Р°РІРЅС‹Рј РјРµРЅСЋ в¬‡пёЏ",
        reply_markup=get_main_menu_kb(message.from_user.id)
    )

@dp.message()
async def message_handler(message: types.Message):
    text = message.text.strip()
    user_id = message.from_user.id

    if match_btn(text, "Р“Р»Р°РІРЅРѕРµ РјРµРЅСЋ"):
        await message.answer("Р“Р»Р°РІРЅРѕРµ РјРµРЅСЋ", reply_markup=get_main_menu_kb(user_id))
        user_context.pop(user_id, None)
        return

    if text.startswith("вќЊ РћС‚РјРµРЅРёС‚СЊ"):
        parts = text.replace("вќЊ РћС‚РјРµРЅРёС‚СЊ", "").strip().split()
        if len(parts) != 2:
            await message.answer("РћС€РёР±РєР° С„РѕСЂРјР°С‚Р°! РџРѕРїСЂРѕР±СѓР№С‚Рµ РѕС‚РјРµРЅСѓ СЃРЅРѕРІР° РёР· СЂР°СЃРїРёСЃР°РЅРёСЏ.", reply_markup=get_main_menu_kb(user_id))
            return
        date_s, time_s = parts
        data = load_data()
        record = next((item for item in data["schedule"] if item["date"]==date_s and item["time"]==time_s and item.get("user_id")==user_id and item.get("status")!="РѕС‚РјРµРЅРµРЅРѕ"), None)
        if not record:
            await message.answer("Р—Р°РїРёСЃСЊ РЅРµ РЅР°Р№РґРµРЅР° РёР»Рё СѓР¶Рµ РѕС‚РјРµРЅРµРЅР°.", reply_markup=get_main_menu_kb(user_id))
            return
        dt = safe_datetime(date_s, time_s)
        now = datetime.now()
        if (dt - now).total_seconds() < 0:
            await message.answer("Р­С‚Р° Р·Р°РїРёСЃСЊ РІ РїСЂРѕС€Р»РѕРј.", reply_markup=get_main_menu_kb(user_id))
            return
        if (dt - now).total_seconds() < 12*3600:
            await message.answer(
                "РћС‚РјРµРЅР° СЌС‚РѕРіРѕ Р·Р°РЅСЏС‚РёСЏ РјРµРЅРµРµ С‡РµРј Р·Р° 12 С‡Р°СЃРѕРІ РЅРµРІРѕР·РјРѕР¶РЅР° С‡РµСЂРµР· Р±РѕС‚Р°. "
                f"Р•СЃР»Рё Сѓ РІР°СЃ РёР·РјРµРЅРёР»РёСЃСЊ РїР»Р°РЅС‹, СЃСЂРѕС‡РЅРѕ РЅР°РїРёС€РёС‚Рµ РёРЅСЃС‚СЂСѓРєС‚РѕСЂСѓ Р»РёС‡РЅРѕ: {TELEGRAM_LINK}",
                reply_markup=get_main_menu_kb(user_id)
            )
            return
        record["status"] = "РѕС‚РјРµРЅРµРЅРѕ"
        save_data(data)
        users_to_notify = set(item["user_id"] for item in data["schedule"]) | {YOUR_TELEGRAM_ID}
        for uid in users_to_notify:
            if uid != user_id:
                try:
                    await bot.send_message(uid, f"рџ”” РћСЃРІРѕР±РѕРґРёР»СЃСЏ СЃР»РѕС‚!\nР”Р°С‚Р°: {date_s}, РІСЂРµРјСЏ: {time_s}. РњРѕР¶РЅРѕ Р·Р°РїРёСЃР°С‚СЊСЃСЏ С‡РµСЂРµР· РјРµРЅСЋ.")
                except Exception:
                    pass
        await message.answer(f"вњ… Р—Р°РЅСЏС‚РёРµ {date_s} {time_s} РѕС‚РјРµРЅРµРЅРѕ Рё РґРѕСЃС‚СѓРїРЅРѕ РґР»СЏ РґСЂСѓРіРёС… СѓС‡РµРЅРёРєРѕРІ.", reply_markup=get_main_menu_kb(user_id))
        return

    # --- ADMIN PANEL ---
    if user_id == YOUR_TELEGRAM_ID and match_btn(text, "РђРґРјРёРЅ-РїР°РЅРµР»СЊ"):
        days = get_workdays()
        days_buttons = [f"рџ“† {name} {date}" for name, date in days]
        kb = make_two_row_keyboard(days_buttons, extras=["рџЏ  Р“Р»Р°РІРЅРѕРµ РјРµРЅСЋ"])
        markup = ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
        user_context[user_id] = {"admin_mode": True, "admin_step": "admin_day", "days": [date for _, date in days]}
        await message.answer("рџ›ЎпёЏ РђРґРјРёРЅ-РїР°РЅРµР»СЊ\nР’С‹Р±РµСЂРёС‚Рµ РґРµРЅСЊ РґР»СЏ СѓРїСЂР°РІР»РµРЅРёСЏ:", reply_markup=markup)
        return

    if user_context.get(user_id, {}).get("admin_mode") and user_context[user_id].get("admin_step") == "admin_day":
        btn_date = extract_date_from_btn(text)
        if btn_date and btn_date in user_context[user_id]["days"]:
            selected_date = btn_date
            times = get_times()
            data = load_data()
            slot_buttons = []
            for t in times:
                slot = next((i for i in data["schedule"] if i["date"] == selected_date and i["time"] == t and i.get("status") != "РѕС‚РјРµРЅРµРЅРѕ"), None)
                if slot and slot.get("status") == "Р·Р°Р±Р»РѕРєРёСЂРѕРІР°РЅРѕ":
                    slot_buttons.append(f"в›” {t}")
                elif slot:
                    slot_buttons.append(f"рџ”ґ {t}")
                else:
                    slot_buttons.append(f"рџџў {t}")
            slot_buttons.append("вќ— РћС‚РјРµРЅРёС‚СЊ РІСЃРµ Р·Р°РЅСЏС‚РёСЏ РЅР° РґРµРЅСЊ")
            kb = make_two_row_keyboard(slot_buttons, extras=["рџЏ  Р“Р»Р°РІРЅРѕРµ РјРµРЅСЋ", "рџ”™ РќР°Р·Р°Рґ"])
            markup = ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
            user_context[user_id].update({"admin_step": "admin_time", "admin_day": selected_date, "times": times})
            await message.answer(
                f"Р”РµРЅСЊ {selected_date}: РІС‹Р±РµСЂРёС‚Рµ СЃР»РѕС‚ РёР»Рё РѕС‚РјРµРЅРёС‚Рµ РІРµСЃСЊ РґРµРЅСЊ.",
                reply_markup=markup
            )
            return
        else:
            await message.answer("РџРѕР¶Р°Р»СѓР№СЃС‚Р°, РІС‹Р±РµСЂРёС‚Рµ РґРµРЅСЊ РёР· РїСЂРµРґР»РѕР¶РµРЅРЅС‹С… РєРЅРѕРїРѕРє.", reply_markup=ReplyKeyboardMarkup(
                keyboard=[[KeyboardButton(text=f"рџ“† {name} {date}") for name, date in get_workdays()]],
                resize_keyboard=True
            ))
            return

    # --- ADMIN TIME: РѕР±СЂР°Р±РѕС‚РєР° РѕС‚РјРµРЅС‹ РІСЃРµС… Р·Р°РЅСЏС‚РёР№ РЅР° РґРµРЅСЊ ---
    if user_context.get(user_id, {}).get("admin_mode") and user_context[user_id].get("admin_step") == "admin_time":
        # РћР±СЂР°Р±РѕС‚РєР° "РћС‚РјРµРЅРёС‚СЊ РІСЃРµ Р·Р°РЅСЏС‚РёСЏ РЅР° РґРµРЅСЊ"
        if text == "вќ— РћС‚РјРµРЅРёС‚СЊ РІСЃРµ Р·Р°РЅСЏС‚РёСЏ РЅР° РґРµРЅСЊ":
            selected_date = user_context[user_id].get("admin_day")
            data = load_data()
            
            cancelled_count = 0
            for item in data["schedule"]:
                if item["date"] == selected_date and item.get("status") != "РѕС‚РјРµРЅРµРЅРѕ":
                    item["status"] = "РѕС‚РјРµРЅРµРЅРѕ"
                    cancelled_count += 1
                    
                    # РЈРІРµРґРѕРјРёС‚СЊ РїРѕР»СЊР·РѕРІР°С‚РµР»СЏ РѕР± РѕС‚РјРµРЅРµ
                    try:
                        await bot.send_message(
                            item["user_id"],
                            f"вќЊ Р’Р°С€Рµ Р·Р°РЅСЏС‚РёРµ {selected_date} {item['time']} РѕС‚РјРµРЅРµРЅРѕ РёРЅСЃС‚СЂСѓРєС‚РѕСЂРѕРј.\n"
                            f"РџРѕР¶Р°Р»СѓР№СЃС‚Р°, Р·Р°РїРёС€РёС‚РµСЃСЊ РЅР° РґСЂСѓРіРѕРµ РІСЂРµРјСЏ."
                        )
                    except Exception:
                        pass
            
            save_data(data)
            
            await message.answer(
                f"вњ… РћС‚РјРµРЅРµРЅРѕ Р·Р°РЅСЏС‚РёР№ РЅР° {selected_date}: {cancelled_count}\n"
                f"Р’СЃРµ СѓС‡РµРЅРёРєРё РїРѕР»СѓС‡РёР»Рё СѓРІРµРґРѕРјР»РµРЅРёСЏ.",
                reply_markup=get_main_menu_kb(user_id)
            )
            user_context.pop(user_id, None)
            return
        
        # РћР±СЂР°Р±РѕС‚РєР° РІС‹Р±РѕСЂР° РєРѕРЅРєСЂРµС‚РЅРѕРіРѕ СЃР»РѕС‚Р°
        chosen_time = extract_time_from_btn(text)
        if chosen_time and chosen_time in user_context[user_id]["times"]:
            selected_date = user_context[user_id]["admin_day"]
            data = load_data()
            slot = next((i for i in data["schedule"] if i["date"] == selected_date and i["time"] == chosen_time and i.get("status") != "РѕС‚РјРµРЅРµРЅРѕ"), None)
            
            if slot:
                # РЎР»РѕС‚ Р·Р°РЅСЏС‚ - РїРѕРєР°Р·С‹РІР°РµРј РёРЅС„РѕСЂРјР°С†РёСЋ Рё РєРЅРѕРїРєРё СѓРїСЂР°РІР»РµРЅРёСЏ
                student_info = f"рџ”ґ РЎР»РѕС‚ Р·Р°РЅСЏС‚:\nрџ“† {selected_date}\nрџ•’ {chosen_time}\nрџ‘¤ {slot.get('surname','')} {slot.get('name','')}\nрџ“Ќ {slot['address']}"
                kb = [
                    [KeyboardButton(text="вќЊ РћС‚РјРµРЅРёС‚СЊ Р·Р°РЅСЏС‚РёРµ")],
                    [KeyboardButton(text="рџЏ  Р“Р»Р°РІРЅРѕРµ РјРµРЅСЋ"), KeyboardButton(text="рџ”™ РќР°Р·Р°Рґ")]
                ]
                user_context[user_id]["admin_selected_slot"] = {"date": selected_date, "time": chosen_time}
                await message.answer(student_info, reply_markup=ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True))
                return
            else:
                # РЎР»РѕС‚ СЃРІРѕР±РѕРґРµРЅ - РїСЂРµРґР»Р°РіР°РµРј Р·Р°Р±Р»РѕРєРёСЂРѕРІР°С‚СЊ
                kb = [
                    [KeyboardButton(text="в›” Р—Р°Р±Р»РѕРєРёСЂРѕРІР°С‚СЊ СЃР»РѕС‚")],
                    [KeyboardButton(text="рџЏ  Р“Р»Р°РІРЅРѕРµ РјРµРЅСЋ"), KeyboardButton(text="рџ”™ РќР°Р·Р°Рґ")]
                ]
                user_context[user_id]["admin_selected_slot"] = {"date": selected_date, "time": chosen_time}
                await message.answer(f"рџџў РЎР»РѕС‚ СЃРІРѕР±РѕРґРµРЅ: {selected_date} {chosen_time}", reply_markup=ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True))
                return

    # РћР±СЂР°Р±РѕС‚РєР° РґРµР№СЃС‚РІРёР№ Р°РґРјРёРЅР° РЅР°Рґ РІС‹Р±СЂР°РЅРЅС‹Рј СЃР»РѕС‚РѕРј
    if user_context.get(user_id, {}).get("admin_mode") and user_context[user_id].get("admin_selected_slot"):
        slot_info = user_context[user_id]["admin_selected_slot"]
        
        if text == "вќЊ РћС‚РјРµРЅРёС‚СЊ Р·Р°РЅСЏС‚РёРµ":
            data = load_data()
            record = next((i for i in data["schedule"] if i["date"] == slot_info["date"] and i["time"] == slot_info["time"] and i.get("status") != "РѕС‚РјРµРЅРµРЅРѕ"), None)
            if record:
                record["status"] = "РѕС‚РјРµРЅРµРЅРѕ"
                save_data(data)
                try:
                    await bot.send_message(record["user_id"], f"вќЊ Р’Р°С€Рµ Р·Р°РЅСЏС‚РёРµ {slot_info['date']} {slot_info['time']} РѕС‚РјРµРЅРµРЅРѕ РёРЅСЃС‚СЂСѓРєС‚РѕСЂРѕРј.")
                except Exception:
                    pass
                await message.answer(f"вњ… Р—Р°РЅСЏС‚РёРµ {slot_info['date']} {slot_info['time']} РѕС‚РјРµРЅРµРЅРѕ.", reply_markup=get_main_menu_kb(user_id))
            user_context.pop(user_id, None)
            return
        
        if text == "в›” Р—Р°Р±Р»РѕРєРёСЂРѕРІР°С‚СЊ СЃР»РѕС‚":
            data = load_data()
            data["schedule"].append({
                "date": slot_info["date"],
                "time": slot_info["time"],
                "status": "Р·Р°Р±Р»РѕРєРёСЂРѕРІР°РЅРѕ",
                "user_id": YOUR_TELEGRAM_ID,
                "name": "",
                "surname": "",
                "address": ""
            })
            save_data(data)
            await message.answer(f"в›” РЎР»РѕС‚ {slot_info['date']} {slot_info['time']} Р·Р°Р±Р»РѕРєРёСЂРѕРІР°РЅ.", reply_markup=get_main_menu_kb(user_id))
            user_context.pop(user_id, None)
            return

    # --- USER choose_day: РїРѕ РґР°С‚Рµ РёР· РєРЅРѕРїРєРё ---
    if user_context.get(user_id, {}).get("step") == "choose_day":
        btn_date = extract_date_from_btn(text)
        if btn_date and btn_date in user_context[user_id]["days"]:
            selected_day = btn_date
            times = get_times()
            data = load_data()
            times_buttons = []
            for t in times:
                busy = any(item["date"]==selected_day and item["time"]==t and item.get("status")!="РѕС‚РјРµРЅРµРЅРѕ" for item in data["schedule"])
                if busy:
                    times_buttons.append(f"рџ”ґ {t} (Р·Р°РЅСЏС‚Рѕ)")
                else:
                    times_buttons.append(f"рџџў {t}")
            kb = make_two_row_keyboard(times_buttons, extras=["рџЏ  Р“Р»Р°РІРЅРѕРµ РјРµРЅСЋ", "рџ”™ РќР°Р·Р°Рґ"])
            markup = ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
            user_context[user_id]["step"] = "choose_time"
            user_context[user_id]["date"] = selected_day
            await message.answer(f"рџ•’ РЁР°Рі 2: Р’С‹Р±РµСЂРёС‚Рµ РІСЂРµРјСЏ РґР»СЏ {selected_day}:", reply_markup=markup)
            return
        else:
            await message.answer("РџРѕР¶Р°Р»СѓР№СЃС‚Р°, РІС‹Р±РµСЂРёС‚Рµ РґРµРЅСЊ РёР· РєРЅРѕРїРѕРє.", reply_markup=ReplyKeyboardMarkup(
                keyboard=[[KeyboardButton(text=f"рџ“† {name} {date}") for name, date in get_workdays()]],
                resize_keyboard=True
            ))
            return

    # --- USER choose_time: СѓРЅРёРІРµСЂСЃР°Р»СЊРЅС‹Р№ ---
    if user_context.get(user_id, {}).get("step") == "choose_time":
        chosen_time = extract_time_from_btn(text)
        if not chosen_time or chosen_time not in get_times():
            await message.answer("РџРѕР¶Р°Р»СѓР№СЃС‚Р°, РІС‹Р±РµСЂРёС‚Рµ РІСЂРµРјСЏ РёР· РєРЅРѕРїРѕРє.", reply_markup=ReplyKeyboardMarkup(
                keyboard=[[KeyboardButton(text=f"рџџў {t}") for t in get_times()]],
                resize_keyboard=True
            ))
            return

        selected_day = user_context[user_id]["date"]
        busy = any(item["date"]==selected_day and item["time"]==chosen_time and item.get("status")!="РѕС‚РјРµРЅРµРЅРѕ" for item in load_data()["schedule"])
        if busy:
            await message.answer("Р­С‚Рѕ РІСЂРµРјСЏ СѓР¶Рµ Р·Р°РЅСЏС‚Рѕ. Р’С‹Р±РµСЂРёС‚Рµ РґСЂСѓРіРѕР№ СЃР»РѕС‚!", reply_markup=get_main_menu_kb(user_id))
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
                kb = make_two_row_keyboard([], extras=["рџЏ  Р“Р»Р°РІРЅРѕРµ РјРµРЅСЋ", "рџ”™ РќР°Р·Р°Рґ", "вњ… РћСЃС‚Р°РІРёС‚СЊ Р°РґСЂРµСЃ"])
                await message.answer(f"рџ“Ќ Р’Р°С€ Р°РґСЂРµСЃ: {address}\nР•СЃР»Рё РЅСѓР¶РЅРѕ РёР·РјРµРЅРёС‚СЊ вЂ” РЅР°РїРёС€РёС‚Рµ РЅРѕРІС‹Р№.\nР•СЃР»Рё РїРѕРґС…РѕРґРёС‚ вЂ” РЅР°Р¶РјРёС‚Рµ 'РћСЃС‚Р°РІРёС‚СЊ Р°РґСЂРµСЃ'.", reply_markup=ReplyKeyboardMarkup(keyboard=kb,resize_keyboard=True))
            else:
                kb = make_two_row_keyboard([], extras=["рџЏ  Р“Р»Р°РІРЅРѕРµ РјРµРЅСЋ", "рџ”™ РќР°Р·Р°Рґ"])
                await message.answer("рџ“Ќ Р’РІРµРґРёС‚Рµ Р°РґСЂРµСЃ (РєСѓРґР° РїРѕРґСЉРµС…Р°С‚СЊ):", reply_markup=ReplyKeyboardMarkup(keyboard=kb,resize_keyboard=True))
            return
        else:
            kb = make_two_row_keyboard([], extras=["рџЏ  Р“Р»Р°РІРЅРѕРµ РјРµРЅСЋ", "рџ”™ РќР°Р·Р°Рґ"])
            await message.answer("рџ‘¤ Р’РІРµРґРёС‚Рµ С„Р°РјРёР»РёСЋ Рё РёРјСЏ (РїСЂРёРјРµСЂ: РРІР°РЅРѕРІ РРІР°РЅ):", reply_markup=ReplyKeyboardMarkup(keyboard=kb,resize_keyboard=True))
            return

    # --- USER: СЌС‚Р°Рї РІРІРѕРґР° Р¤РРћ ---
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
            kb = make_two_row_keyboard([], extras=["рџЏ  Р“Р»Р°РІРЅРѕРµ РјРµРЅСЋ", "рџ”™ РќР°Р·Р°Рґ", "вњ… РћСЃС‚Р°РІРёС‚СЊ Р°РґСЂРµСЃ"])
            await message.answer(f"рџ“Ќ Р’Р°С€ Р°РґСЂРµСЃ: {address}\nР•СЃР»Рё РЅСѓР¶РЅРѕ РёР·РјРµРЅРёС‚СЊ вЂ” РЅР°РїРёС€РёС‚Рµ РЅРѕРІС‹Р№.\nР•СЃР»Рё РїРѕРґС…РѕРґРёС‚ вЂ” РЅР°Р¶РјРёС‚Рµ 'РћСЃС‚Р°РІРёС‚СЊ Р°РґСЂРµСЃ'.", reply_markup=ReplyKeyboardMarkup(keyboard=kb,resize_keyboard=True))
        else:
            kb = make_two_row_keyboard([], extras=["рџЏ  Р“Р»Р°РІРЅРѕРµ РјРµРЅСЋ", "рџ”™ РќР°Р·Р°Рґ"])
            await message.answer("рџ“Ќ Р’РІРµРґРёС‚Рµ Р°РґСЂРµСЃ (РєСѓРґР° РїРѕРґСЉРµС…Р°С‚СЊ):", reply_markup=ReplyKeyboardMarkup(keyboard=kb,resize_keyboard=True))
        return

    # --- USER: СЌС‚Р°Рї Р°РґСЂРµСЃ ---
    if user_context.get(user_id, {}).get("step") == "choose_address":
        uid_str = str(user_id)
        if text == "вњ… РћСЃС‚Р°РІРёС‚СЊ Р°РґСЂРµСЃ":
            address = users_info.get(uid_str, {}).get("address")
        else:
            address = text.strip()
            users_info[uid_str] = users_info.get(uid_str, {})
            users_info[uid_str]["address"] = address
            save_users_info(users_info)
        user_context[user_id]["address"] = address
        user_context[user_id]["step"] = "confirm_record"
        kb = make_two_row_keyboard([], extras=["вњ… РџРѕРґС‚РІРµСЂРґРёС‚СЊ Р·Р°РїРёСЃСЊ", "рџ”™ РќР°Р·Р°Рґ", "рџЏ  Р“Р»Р°РІРЅРѕРµ РјРµРЅСЋ"])
        await send_record_confirmation(message, user_id, kb)
        return

    # --- USER: С„РёРЅР°Р»СЊРЅРѕРµ РїРѕРґС‚РІРµСЂР¶РґРµРЅРёРµ ---
    if user_context.get(user_id, {}).get("step") == "confirm_record":
        if text == "вњ… РџРѕРґС‚РІРµСЂРґРёС‚СЊ Р·Р°РїРёСЃСЊ":
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
                f"вњ… Р—Р°РїРёСЃСЊ РїРѕРґС‚РІРµСЂР¶РґРµРЅР°!\n"
                f"рџ“† Р”Р°С‚Р°: {ctx['date']}\n"
                f"рџ•’ Р’СЂРµРјСЏ: {ctx['time']}\n"
                f"рџ‘¤ Р¤РРћ: {ctx['fio']}\n"
                f"рџ“Ќ РђРґСЂРµСЃ: {ctx['address']}"
            )
            await message.answer(msg, reply_markup=get_main_menu_kb(user_id))
            await bot.send_message(YOUR_TELEGRAM_ID, msg, parse_mode="HTML")
            user_context.pop(user_id, None)
            return

    if match_btn(text, "РњРѕС‘ СЂР°СЃРїРёСЃР°РЅРёРµ"):
        await send_user_schedule(message, user_id)
        return

    if match_btn(text, "Р—Р°РїРёСЃР°С‚СЊСЃСЏ РЅР° Р·Р°РЅСЏС‚РёРµ"):
        data = load_data()
        days = get_workdays()
        available_days = []
        days_buttons = []
        for name, date in days:
            if has_day_record(user_id, date):
                days_buttons.append(f"вќЊ {name} {date} (СѓР¶Рµ Р·Р°РїРёСЃР°РЅС‹)")
            elif week_limit(user_id, date) >= 2:
                days_buttons.append(f"рџљ« {name} {date} (Р»РёРјРёС‚)")
            else:
                days_buttons.append(f"рџ“† {name} {date}")
                available_days.append((name, date))

        if not available_days:
            await message.answer("РќРµС‚ РґРѕСЃС‚СѓРїРЅС‹С… РґРЅРµР№ РґР»СЏ Р·Р°РїРёСЃРё.", reply_markup=get_main_menu_kb(user_id))
            return

        kb = make_two_row_keyboard(days_buttons, extras=["рџЏ  Р“Р»Р°РІРЅРѕРµ РјРµРЅСЋ"])
        markup = ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
        user_context[user_id] = {"step": "choose_day", "days": [date for _, date in available_days]}
        await message.answer(
            "рџ“… РЁР°Рі 1: Р’С‹Р±РµСЂРёС‚Рµ РґРµРЅСЊ РґР»СЏ Р·Р°РЅСЏС‚РёСЏ. РЎР»РѕС‚С‹ СЃ вќЊ РёР»Рё рџљ« РЅРµРґРѕСЃС‚СѓРїРЅС‹ РґР»СЏ Р·Р°РїРёСЃРё.",
            reply_markup=markup
        )
        return

    if match_btn(text, "РќР°РїРёСЃР°С‚СЊ РёРЅСЃС‚СЂСѓРєС‚РѕСЂСѓ"):
        await message.answer("вњ‰пёЏ Р”Р»СЏ РѕР±СЂР°С‰РµРЅРёСЏ Рє РёРЅСЃС‚СЂСѓРєС‚РѕСЂСѓ РїРёС€РёС‚Рµ СЃСЋРґР°: " + TELEGRAM_LINK)
        return

    await message.answer("вљ пёЏ РќРµРёР·РІРµСЃС‚РЅР°СЏ РєРѕРјР°РЅРґР° РёР»Рё РЅРµРїСЂР°РІРёР»СЊРЅС‹Р№ С„РѕСЂРјР°С‚. РСЃРїРѕР»СЊР·СѓР№С‚Рµ РјРµРЅСЋ.", reply_markup=get_main_menu_kb(user_id))

async def auto_update_code():
    """
    РђРІС‚РѕРјР°С‚РёС‡РµСЃРєР°СЏ РїСЂРѕРІРµСЂРєР° РѕР±РЅРѕРІР»РµРЅРёР№ РєРѕРґР° СЃ GitHub РєР°Р¶РґС‹Рµ 5 РјРёРЅСѓС‚.
    РџСЂРё РѕР±РЅР°СЂСѓР¶РµРЅРёРё РёР·РјРµРЅРµРЅРёР№ - РїРµСЂРµР·Р°РїСѓСЃРє Р±РѕС‚Р°.
    """
    while True:
        try:
            await asyncio.sleep(300)  # РџСЂРѕРІРµСЂРєР° РєР°Р¶РґС‹Рµ 5 РјРёРЅСѓС‚ (300 СЃРµРєСѓРЅРґ)
            
            logging.info("рџ”Ќ РџСЂРѕРІРµСЂРєР° РѕР±РЅРѕРІР»РµРЅРёР№ СЃ GitHub...")
            
            async with aiohttp.ClientSession() as session:
                async with session.get(GITHUB_RAW_URL) as response:
                    if response.status == 200:
                        new_code = await response.text()
                        
                        # Р§РёС‚Р°РµРј С‚РµРєСѓС‰РёР№ РєРѕРґ
                        with open(__file__, "r", encoding="utf-8") as f:
                            current_code = f.read()
                        
                        # РЎСЂР°РІРЅРёРІР°РµРј
                        if new_code != current_code:
                            logging.info("вњ… РќР°Р№РґРµРЅРѕ РѕР±РЅРѕРІР»РµРЅРёРµ! РџСЂРёРјРµРЅСЏСЋ...")
                            
                            # РЎРѕС…СЂР°РЅСЏРµРј РЅРѕРІС‹Р№ РєРѕРґ
                            with open(__file__, "w", encoding="utf-8") as f:
                                f.write(new_code)
                            
                            # РЈРІРµРґРѕРјР»СЏРµРј Р°РґРјРёРЅР°
                            try:
                                await bot.send_message(
                                    YOUR_TELEGRAM_ID,
                                    "рџ”„ РћР±РЅР°СЂСѓР¶РµРЅРѕ РѕР±РЅРѕРІР»РµРЅРёРµ РєРѕРґР°!\nР‘РѕС‚ РїРµСЂРµР·Р°РїСѓСЃРєР°РµС‚СЃСЏ С‡РµСЂРµР· 3 СЃРµРєСѓРЅРґС‹..."
                                )
                            except Exception:
                                pass
                            
                            await asyncio.sleep(3)
                            
                            # РџРµСЂРµР·Р°РїСѓСЃРє
                            logging.info("рџ”„ РџРµСЂРµР·Р°РїСѓСЃРє Р±РѕС‚Р°...")
                            os.execv(sys.executable, [sys.executable] + sys.argv)
                        else:
                            logging.info("вњ”пёЏ РљРѕРґ Р°РєС‚СѓР°Р»РµРЅ, РѕР±РЅРѕРІР»РµРЅРёР№ РЅРµС‚.")
                    else:
                        logging.warning(f"вљ пёЏ РћС€РёР±РєР° Р·Р°РіСЂСѓР·РєРё СЃ GitHub: {response.status}")
                        
        except Exception as e:
            logging.error(f"вќЊ РћС€РёР±РєР° Р°РІС‚РѕРѕР±РЅРѕРІР»РµРЅРёСЏ: {e}")
            await asyncio.sleep(300)  # РџРѕРІС‚РѕСЂ С‡РµСЂРµР· 5 РјРёРЅСѓС‚ РґР°Р¶Рµ РїСЂРё РѕС€РёР±РєРµ

async def send_reminders():
    pass

async def main():
    print("=== РќРѕРІС‹Р№ Р·Р°РїСѓСЃРє DRIVE_BOT ===")
    asyncio.create_task(send_reminders())
    asyncio.create_task(auto_update_code())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
