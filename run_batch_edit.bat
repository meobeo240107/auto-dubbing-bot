@echo off
chcp 65001 >nul
title Auto Batch Video Dubbing Processor
echo ========================================================
echo   AUTO BATCH VIDEO DUBBING PROCESSOR (OFFLINE / LOCAL)
echo ========================================================
echo.
echo [1] Thư mục chứa video gốc : D:\video_input
echo [2] Thư mục lưu thành phẩm : D:\banve
echo.
echo Đang quét và bắt đầu xử lý tuần tự từng video...
echo.

cd /d "%~dp0backend"
call ".\venv\Scripts\python.exe" "batch_processor.py" --input "D:\video_input" --output "D:\banve"

echo.
echo ========================================================
echo   HOÀN TẤT! Video thành phẩm đã được lưu tại D:\banve
echo ========================================================
pause
