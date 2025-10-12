@echo off
title Drive Lessons Bot
cd /d %~dp0
if not exist venv (
    echo Создаю виртуальное окружение...
    python -m venv venv
)
call venv\Scripts\activate.bat
pip install --upgrade pip
pip install -r requirements.txt
echo.
echo ================================
echo ✅ Бот запускается...
echo ================================
python bot.py
pause
