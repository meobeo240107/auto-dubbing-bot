# AutoDub Pipeline v2 — Bàn giao

Thư mục này chứa cây mã nguồn đầy đủ của nhánh `refactor/pipeline-v2` cùng toàn
bộ thay đổi ổn định hóa Pipeline v2 trong vòng review cuối.

## Nội dung

- `backend/`: Downloader, Demucs, Whisper, EasyOCR, Gemini Translation,
  Timing Solver, TTS, RVC, FFmpeg Mixer, QC Gate, API và Telegram bot.
- `frontend/`: Electron/React UI, preload bridge, dependencies và production build.
- `MyVoiceModel_v2/`: model và index RVC hiện có.
- `tests/`: unit/regression tests Pipeline v2.
- `docs/`: kiến trúc và hướng dẫn rollout.
- `.git/`: lịch sử Git của repository.
- `AutoDub_Pipeline_v2_review.patch`: patch hợp nhất có thể áp dụng lại lên bản
  gốc của nhánh `refactor/pipeline-v2`.

## Kết quả kiểm định code

- 125 file Python parse thành công.
- 72/72 backend tests đạt.
- Frontend lint và production build đạt.
- `npm audit`: 0 vulnerability.
- Patch đã qua `git apply --check`.

## Trạng thái máy tại thời điểm bàn giao

Preflight hiện báo `ready=false`: Python chạy ngoài venv còn thiếu Torch,
TorchAudio, Demucs, EasyOCR, Faster Whisper, FastAPI, Telegram và một số module
khác; `BOT_TOKEN`/`GEMINI_API_KEY` chưa được cấu hình; Pipeline vẫn ở `legacy`;
RVC model có mặt nhưng thiếu `rvc-python`. FFmpeg, ffprobe và NVENC đã đạt.

Không chạy production trước khi tạo `backend/venv`, cài dependencies, sao chép
`backend/.env.example` thành `backend/.env`, điền secrets và nhận kết quả
`ready=True` từ:

```powershell
cd backend
.\venv\Scripts\python.exe -m pipeline_v2.preflight --project-root .. --interface all
```

Lượt video thật đầu tiên nên dùng `QC_GATE_POLICY=report_only`. Xem checklist
đầy đủ tại `docs/pipeline_v2_rollout.md`.
