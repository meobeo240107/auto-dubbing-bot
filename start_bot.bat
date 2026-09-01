@echo off
:: ==========================================
:: SCRIPT KHỞI ĐỘNG AUTO VIDEO DUBBING BOT
:: ==========================================

set "PROJECT_DIR=%~dp0"

:: Khởi động Frontend (Log Viewer) ngầm
cd /d "%PROJECT_DIR%frontend"
start /b cmd /c "npm run dev"

:: Đợi 2 giây để Frontend kịp chạy
ping 127.0.0.1 -n 3 > NUL

:: Dọn dẹp tiến trình telegram_bot cũ nếu có để tránh chạy trùng lặp
powershell -Command "Get-CimInstance Win32_Process -Filter \"Name like 'python%'\" | Where-Object { $_.CommandLine -like '*telegram_bot.py*' } | Stop-Process -Force" >NUL 2>&1

:: Khởi động Backend (Telegram Bot) ngầm
cd /d "%PROJECT_DIR%backend"
if exist "venv\Scripts\python.exe" (
  start /b "" "venv\Scripts\python.exe" telegram_bot.py
) else (
  start /b "" py telegram_bot.py
)
