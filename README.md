# AutoDub Video Bot (Python + AI)

Công cụ tự động tải video, tách âm thanh nhân vật (Demucs), nhận dạng giọng nói (Whisper Large-v3), dịch phụ đề (Gemini AI), lồng tiếng bằng AI Clone Giọng (RVC) và tự động nhận diện khớp vị trí phụ đề gốc (EasyOCR).

## 🚀 Tính năng chính
- **Tải video đa nền tảng**: TikTok, Douyin, Xiaohongshu, YouTube, Facebook, Instagram.
- **Tách Vocal sạch**: Dùng **Demucs (htdemucs_ft)** loại bỏ hoàn toàn âm nhạc nền để Whisper nhận diện chính xác.
- **Nhận diện giọng nói**: Whisper Large-v3 trích xuất phụ đề cực chuẩn.
- **Dịch thông minh với Gemini**: Dịch ngữ cảnh sát nghĩa, tự động bám theo nội dung video.
- **Lồng tiếng RVC Voice Clone**: Chuyển giọng TTS sang giọng nói cá nhân đã qua huấn luyện.
- **Robust Y-Tracking (EasyOCR)**: Tự động phát hiện vị trí phụ đề gốc để đè đè chữ tiếng Việt chính xác.
- **Bot Telegram**: Điều khiển và nhận video trực tiếp qua ứng dụng Telegram.

## 🛠️ Cấu trúc thư mục
- `backend/`: Mã nguồn Python xử lý AI, OCR, RVC và Telegram Bot.
- `frontend/`: Giao diện ứng dụng (Desktop / Electron / Vite UI).
- `start_bot.bat`: Script khởi động Bot nhanh trên Windows.

## 📌 Hướng dẫn chạy Tool
1. Tạo môi trường virtualenv và cài đặt dependencies:
   ```bash
   cd backend
   python -m venv venv
   .\venv\Scripts\activate
   pip install -r requirements.txt
   ```
2. Chạy Telegram Bot:
   ```bash
   python telegram_bot.py
   ```
