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
   cd ..
   # Cài PyTorch + TorchAudio CUDA phù hợp driver NVIDIA trước.
   # Chọn lệnh Windows chính xác tại https://pytorch.org/get-started/locally/
   pip install -r requirements.txt
   cd backend
   Copy-Item .env.example .env
   # Điền BOT_TOKEN/GEMINI_API_KEY và các thư mục AUTODUB_* trong .env.
   ```
2. Chạy Telegram Bot:
   ```bash
   # Kiểm tra dependency, FFmpeg/NVENC, CUDA, thư mục ghi và secrets trước.
   .\venv\Scripts\python.exe -m pipeline_v2.preflight --project-root .. --interface telegram
   python telegram_bot.py
   ```

Không chạy video production nếu preflight còn `error`; với Pipeline v2, kiểm tra
thêm `pipeline:config` đang là `v2`. Unit test không thay thế lượt thử end-to-end
với model, API key và driver thật của máy vận hành.

## Pipeline v2 (opt-in)

Pipeline cũ vẫn là mặc định. Pipeline v2 bổ sung checkpoint theo stage, process
GPU riêng, timing solver, FFmpeg ducking/loudness và QC gate. Xem hướng dẫn bật
`shadow`/`v2`, feature flag và rollback tại
[`docs/pipeline_v2_rollout.md`](docs/pipeline_v2_rollout.md).

Pipeline v2 giới hạn tài nguyên theo batch thay vì theo độ dài video. Vì vậy cùng
một luồng xử lý được dùng cho video ngắn và video dài: dịch/OCR/TTS/RVC có batch
checkpoint, mixer tạo voice bus phân tầng để không vượt giới hạn dòng lệnh
Windows, còn FFmpeg/Demucs/Whisper tiếp tục xử lý streaming hoặc theo segment.
