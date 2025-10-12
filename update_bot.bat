@echo off
cd /d %~dp0
echo 🔄 Обновление бота из GitHub...
powershell -Command "Invoke-WebRequest https://raw.githubusercontent.com/uryashev666-spec/drive_bot/main/bot.py -OutFile bot.py"
echo ✅ Обновлено. Перезапускаю...
start run_bot.bat
exit
