@echo off
:: ==========================================
:: SCRIPT KHỞI ĐỘNG AUTO VIDEO DUBBING BOT
:: ==========================================

:: Đặt đường dẫn môi trường cho Node.js (nếu cần)
set PATH=%PATH%;C:\Program Files\nodejs

:: Khởi động Frontend (Log Viewer) ngầm
cd C:\Users\admin\.gemini\antigravity\scratch\video-dubbing-app\frontend
start /b cmd /c "npm run dev"

:: Đợi 2 giây để Frontend kịp chạy
timeout /t 2 /nobreak > NUL

:: Khởi động Backend (Telegram Bot) ngầm
cd C:\Users\admin\.gemini\antigravity\scratch\video-dubbing-app\backend
start /b C:\Users\admin\.gemini\antigravity\scratch\video-dubbing-app\backend\venv\Scripts\python.exe telegram_bot.py
