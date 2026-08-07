"""
Telegram Bot - Auto Video Dubbing
Gửi link video → Bot tự động tải, tạo phụ đề, lồng tiếng, gửi lại video.
"""
import torch
import os
import sys
import asyncio
import time
import subprocess

# CẤP CỨU: Chặn VĨNH VIỄN tất cả các cửa sổ terminal (cmd) đen nháy lên do các thư viện bên thứ 3 (Whisper, PyDub, OCR) gọi ngầm ffmpeg.
if os.name == 'nt':
    original_init = subprocess.Popen.__init__
    def patched_init(self, *args, **kwargs):
        if hasattr(subprocess, 'CREATE_NO_WINDOW'):
            kwargs['creationflags'] = kwargs.get('creationflags', 0) | subprocess.CREATE_NO_WINDOW
        if 'startupinfo' not in kwargs:
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            kwargs['startupinfo'] = startupinfo
        original_init(self, *args, **kwargs)
    subprocess.Popen.__init__ = patched_init

import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Load .env local file
env_file = os.path.join(os.path.dirname(__file__), ".env")
if os.path.exists(env_file):
    with open(env_file, "r", encoding="utf-8") as f:
        for line in f:
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.strip().split("=", 1)
                os.environ[k.strip()] = v.strip().strip('"').strip("'")

# ===== CẤU HÌNH =====
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "YOUR_GEMINI_API_KEY")
FPT_API_KEY = os.getenv("FPT_API_KEY", "YOUR_FPT_API_KEY")

# Import các module xử lý từ backend
sys.path.insert(0, os.path.dirname(__file__))

# Đảm bảo console hỗ trợ UTF-8 để không bị lỗi UnicodeEncodeError
import io
if isinstance(sys.stdout, io.TextIOWrapper):
    sys.stdout.reconfigure(encoding='utf-8')
if isinstance(sys.stderr, io.TextIOWrapper):
    sys.stderr.reconfigure(encoding='utf-8')

from ai_utils import extract_subtitles_whisper, translate_subtitles, save_srt, generate_dubbing_audio
from video_utils import extract_audio_from_video, mix_audio_pydub, process_video

WORKSPACE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "workspace"))
os.makedirs(WORKSPACE, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("app.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)
logging.getLogger("httpx").setLevel(logging.WARNING)

# ===== LỆNH /start =====
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome = (
        "🎬 *Auto Video Dubbing Bot*\n\n"
        "Gửi cho tôi link video từ bất kỳ nền tảng nào:\n"
        "• Xiaohongshu (小红书)\n"
        "• TikTok\n"
        "• YouTube\n"
        "• Douyin\n"
        "• Facebook\n"
        "• Instagram\n\n"
        "Bot sẽ tự động:\n"
        "1️⃣ Tải video\n"
        "2️⃣ Nhận dạng giọng nói (Whisper AI)\n"
        "3️⃣ Dịch phụ đề sang Tiếng Việt\n"
        "4️⃣ Lồng tiếng Tiếng Việt\n"
        "5️⃣ Gửi lại video đã xử lý\n\n"
        "📌 *Lệnh:*\n"
        "/start - Hiện hướng dẫn\n"
        "/status - Kiểm tra trạng thái\n"
    )
    await update.message.reply_text(welcome, parse_mode="Markdown")


# ===== LỆNH /status =====
async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "✅ Bot đang hoạt động!\n"
        f"📂 Workspace: {WORKSPACE}\n"
        "🎯 Gửi link video để bắt đầu."
    )


import shared_state
shared_state.stop_requested = False

async def cmd_stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    import shared_state
    shared_state.stop_requested = True
    
    # Xóa hàng đợi
    while not global_queue.empty():
        try:
            global_queue.get_nowait()
            global_queue.task_done()
        except:
            pass
            
    global queue_counter
    queue_counter = 0
            
    await update.message.reply_text("🛑 Đang hủy toàn bộ quá trình tải và xử lý video. Vui lòng đợi trong giây lát...")
    
    # Kill các tiến trình con (yt-dlp, ffmpeg, demucs...)
    try:
        import psutil
        current_process = psutil.Process(os.getpid())
        children = current_process.children(recursive=True)
        for child in children:
            try:
                child.kill()
            except Exception:
                pass
        await update.message.reply_text("✅ Đã tiêu diệt xong các tiến trình chạy ngầm.")
    except Exception as e:
        logger.error(f"Error killing children: {e}")

import re

global_queue = asyncio.Queue()
queue_counter = 0
worker_task = None

async def send_video_safely(context, chat_id, final_video, caption, status_msg, url_or_filename):
    file_size = os.path.getsize(final_video)
    max_size = 49.5 * 1024 * 1024
    
    if file_size <= max_size:
        with open(final_video, 'rb') as vf:
            await context.bot.send_video(
                chat_id=chat_id, video=vf, caption=caption,
                supports_streaming=True, read_timeout=600, write_timeout=600, connect_timeout=600
            )
        await status_msg.edit_text(f"✅ *Hoàn tất!*\n`{url_or_filename}`", parse_mode="Markdown")
        return

    # Nếu file quá lớn (do chất lượng 720p ép buộc), tiến hành cắt nhỏ video bằng FFmpeg (copy codec không làm giảm chất lượng)
    await status_msg.edit_text(f"✂️ *Video gốc quá lớn ({file_size // (1024*1024)}MB)!*\nBot đang giữ nguyên chất lượng cao (>720p) và tự động cắt thành các phần <50MB để gửi cho bạn...", parse_mode="Markdown")
    
    import math
    import subprocess
    import ffmpeg
    try:
        probe = ffmpeg.probe(final_video)
        duration = float(probe['format']['duration'])
        num_chunks = math.ceil(file_size / max_size)
        chunk_time = duration / num_chunks
        
        base_name = os.path.splitext(final_video)[0]
        CREATE_NO_WINDOW = 0x08000000 if os.name == 'nt' else 0
        
        cmd = [
            'ffmpeg', '-y', '-i', final_video, 
            '-c', 'copy', 
            '-f', 'segment', 
            '-segment_time', str(chunk_time), 
            '-reset_timestamps', '1', 
            f'{base_name}_part%03d.mp4'
        ]
        await asyncio.to_thread(subprocess.run, cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=CREATE_NO_WINDOW)
        
        import glob
        parts = sorted(glob.glob(f"{base_name}_part*.mp4"))
        
        for i, part in enumerate(parts, 1):
            if shared_state.stop_requested: raise Exception("Bị hủy bởi lệnh /stop")
            await status_msg.edit_text(f"📤 Đang gửi phần {i}/{len(parts)}...", parse_mode="Markdown")
            part_caption = f"{caption}\n\n(Phần {i}/{len(parts)})" if i == 1 else f"🎬 Phần {i}/{len(parts)}"
            with open(part, 'rb') as vf:
                await context.bot.send_video(
                    chat_id=chat_id, video=vf, caption=part_caption,
                    supports_streaming=True, read_timeout=600, write_timeout=600, connect_timeout=600
                )
        
        await status_msg.edit_text(f"✅ *Đã gửi thành công {len(parts)} phần video chất lượng cao!*\n`{url_or_filename}`", parse_mode="Markdown")
        
    except Exception as e:
        logger.error(f"Error splitting video: {e}")
        await status_msg.edit_text(f"❌ *Lỗi chia nhỏ video:* Không thể gửi file lớn qua Telegram.")

async def video_worker():
    while True:
        job = await global_queue.get()
        try:
            if isinstance(job, dict):
                if job['type'] == 'url':
                    await process_single_url(job['update'], job['context'], job['url'], job['pos'])
                elif job['type'] == 'video':
                    await process_single_video(job['update'], job['context'], job['file_id'], job['filename'], job['pos'])
            else:
                pos, update, context, url = job
                await process_single_url(update, context, url, pos)
        except Exception as e:
            logger.error(f"Worker error: {e}")
        finally:
            import gc, torch
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            global_queue.task_done()

async def process_single_url(update: Update, context: ContextTypes.DEFAULT_TYPE, url: str, pos: int = 1):
    chat_id = update.message.chat_id

    # Thông báo bắt đầu
    remaining = global_queue.qsize()
    status_msg = await update.message.reply_text(
        f"▶️ *Đang xử lý Video thứ {pos} trong hàng đợi:*\n`{url}`\n\n"
        f"⏳ Phía sau còn {remaining} video đang chờ...",
        parse_mode="Markdown"
    )

    import subprocess
    import sys
    CREATE_NO_WINDOW = 0x08000000 if sys.platform == 'win32' else 0

    download_dir = os.path.join(WORKSPACE, "downloads")
    os.makedirs(download_dir, exist_ok=True)
    timestamp = str(int(time.time()))
    
    # Lấy UUID ngẫu nhiên để tránh trùng tên khi tải hàng loạt
    import uuid
    uid = str(uuid.uuid4())[:8]
    output_template = os.path.join(download_dir, f"{timestamp}_{uid}_%(title).30s.%(ext)s")

    try:
        import shared_state
        if shared_state.stop_requested: raise Exception("Bị hủy bởi lệnh /stop")

        # ===== BƯỚC 1: TẢI VIDEO =====
        # Thêm header giả lập trình duyệt để cào tốt hơn (nhất là Xiaohongshu)
        cmd_download = [
            sys.executable, "-m", "yt_dlp",
            "-f", "best[ext=mp4]/best",
            "--merge-output-format", "mp4",
            "-o", output_template,
            "--no-playlist",
            "--restrict-filenames",
            "--socket-timeout", "60",
            "--retries", "3",
            url
        ]
        result = await asyncio.to_thread(subprocess.run, cmd_download, capture_output=True, text=True, timeout=300, creationflags=CREATE_NO_WINDOW)

        if result.returncode != 0:
            await status_msg.edit_text(
                f"❌ *Không thể tải video!*\n\n"
                f"Link: {url}\n"
                f"Lỗi: {result.stderr[:500] if result.stderr else 'Không rõ'}"
            )
            return

        # Tìm file đã tải
        downloaded_files = [f for f in os.listdir(download_dir) if f.startswith(f"{timestamp}_{uid}") and f.endswith(".mp4")]
        if not downloaded_files:
            # Fallback
            all_files = sorted(os.listdir(download_dir),
                             key=lambda x: os.path.getmtime(os.path.join(download_dir, x)), reverse=True)
            downloaded_files = [f for f in all_files if f.endswith(".mp4")]

        if not downloaded_files:
            await status_msg.edit_text("❌ Tải xong nhưng không tìm thấy file video.")
            return

        video_path = os.path.join(download_dir, downloaded_files[0])
        # Loại bỏ extension và dấu chấm thừa ở cuối (Windows tự cắt dấu chấm cuối trong tên thư mục)
        base_name = os.path.splitext(downloaded_files[0])[0].rstrip('.')

        # Chuẩn bị thư mục output
        out_dir = os.path.join(WORKSPACE, base_name)
        os.makedirs(out_dir, exist_ok=True)

        original_audio = os.path.join(out_dir, "original.wav")
        srt_original = os.path.join(out_dir, "original.srt")
        srt_translated = os.path.join(out_dir, "translated.srt")
        dubbing_dir = os.path.join(out_dir, "dubbing")
        mixed_audio = os.path.join(out_dir, "mixed.wav")
        final_video = os.path.join(out_dir, f"final_{base_name}.mp4")

        # ===== BƯỚC 2: TÁCH ÂM THANH =====
        start_time = time.time()
        await status_msg.edit_text(
            f"✅ *Tải thành công!*\n`{url}`\n\n"
            "🎧 *Bước 2/6:* Đang trích xuất âm thanh gốc...",
            parse_mode="Markdown"
        )
        if shared_state.stop_requested: raise Exception("Bị hủy bởi lệnh /stop")
        result = await asyncio.to_thread(extract_audio_from_video, video_path, original_audio)
        if not result or not os.path.exists(original_audio):
            await status_msg.edit_text(f"❌ Không thể trích xuất âm thanh từ video.\n`{url}`", parse_mode="Markdown")
            return

        # ===== BƯỚC 2.5: TÁCH VOCAL BẰNG DEMUCS =====
        await status_msg.edit_text(
            f"🎧 *Trích xuất xong!*\n`{url}`\n\n"
            "🧠 *Bước 2.5/6:* AI Demucs đang tách giọng nhân vật khỏi nhạc nền (Sẽ hơi lâu)...",
            parse_mode="Markdown"
        )
        from video_utils import separate_vocals_demucs
        if shared_state.stop_requested: raise Exception("Bị hủy bởi lệnh /stop")
        vocals_audio, no_vocals_audio = await asyncio.to_thread(separate_vocals_demucs, original_audio, out_dir)

        # ===== BƯỚC 3: NHẬN DẠNG GIỌNG NÓI =====
        await status_msg.edit_text(
            f"🧠 *Tách âm thanh nền xong!*\n`{url}`\n\n"
            "🤖 *Bước 3/6:* Whisper AI đang nhận dạng từ Vocal sạch...",
            parse_mode="Markdown"
        )
        # Sử dụng vocals_audio (giọng sạch) thay vì original_audio
        if shared_state.stop_requested: raise Exception("Bị hủy bởi lệnh /stop")
        srt_segments = await asyncio.to_thread(extract_subtitles_whisper, vocals_audio, srt_original)

        # ===== BƯỚC 3.5: KIỂM TRA VỊ TRÍ PHỤ ĐỀ CHÍNH VÀ QUÉT PHỤ ĐỀ CÂM =====
        await status_msg.edit_text("👀 *Bước 3.5/6:* Đang quét vùng phụ đề cố định (OCR)...", parse_mode="Markdown")
        from ocr_utils import perform_video_ocr, extract_silent_subtitles_from_gaps
        from ass_utils import generate_ass_file
        try:
            if shared_state.stop_requested: raise Exception("Bị hủy bởi lệnh /stop")
            _, vid_w, vid_h, main_y_pct = await asyncio.to_thread(perform_video_ocr, video_path, target_lang="vi", sample_rate=1.0, api_key=GEMINI_API_KEY, srt_segments=srt_segments)
            
            floating_segments = []
            
            # XỬ LÝ THỜI GIAN CHUẨN KHI LÀM SUB & LỒNG TIẾNG (Chống lệch giọng)
            import datetime
            for i in range(len(srt_segments) - 1):
                if srt_segments[i].end > srt_segments[i+1].start:
                    new_end = srt_segments[i+1].start - datetime.timedelta(seconds=0.05)
                    if new_end > srt_segments[i].start:
                        srt_segments[i].end = new_end
                    else:
                        srt_segments[i].end = srt_segments[i].start + datetime.timedelta(seconds=0.1)

            for i, seg in enumerate(srt_segments, 1):
                seg.index = i
        except Exception as e:
            logger.error(f"OCR Error: {e}", exc_info=True)
            vid_w, vid_h, main_y_pct, floating_segments = 1920, 1080, 0.88, []
        finally:
            from ocr_utils import release_ocr_reader
            release_ocr_reader()

        # ===== BƯỚC 4: DỊCH PHỤ ĐỀ =====
        await status_msg.edit_text(
            f"🤖 *Nhận dạng xong ({len(srt_segments)} đoạn)!*\n`{url}`\n\n"
            "🌐 *Bước 4/6:* Đang dùng Gemini AI để dịch chuẩn ngữ cảnh...",
            parse_mode="Markdown"
        )
        if shared_state.stop_requested: raise Exception("Bị hủy bởi lệnh /stop")
        translated_segments = await asyncio.to_thread(translate_subtitles, srt_segments, "vi", api_key=GEMINI_API_KEY, video_path=video_path)
        await asyncio.to_thread(save_srt, translated_segments, srt_translated)

        # (Di chuyển BƯỚC 4.5 xuống sau BƯỚC 5 để đồng bộ thời gian biến mất của phụ đề với audio)

        # ===== BƯỚC 5: LỒNG TIẾNG =====
        await status_msg.edit_text(
            "🗣️ *Bước 5/6:* Đang lồng tiếng AI (Giọng Hoài My)...",
            parse_mode="Markdown"
        )
        # Khôi phục giọng RVC (Đáng yêu)
        rvc_model_path = None
        models_dir = os.path.join(WORKSPACE, "models", "rvc")
        if os.path.exists(models_dir):
            for f in os.listdir(models_dir):
                if f.endswith(".pth"):
                    rvc_model_path = os.path.join(models_dir, f)
                    break
                    
        v_source = "rvc" if rvc_model_path else "edge"
        if rvc_model_path:
            v_param = rvc_model_path
        else:
            # from audio_analysis import detect_gender
            # gender = detect_gender(vocals_audio)
            # v_param = "vi-VN-HoaiMyNeural" if gender == "female" else "vi-VN-NamMinhNeural"
            v_param = "vi-VN-HoaiMyNeural"  # Tạm thời cố định giọng nữ
        
        dubbing_audio_files = await generate_dubbing_audio(
            translated_segments, dubbing_dir, voice_source=v_source, voice_param=v_param
        )
        
        # ĐỒNG BỘ THỜI GIAN BIẾN MẤT CỦA PHỤ ĐỀ THEO GIỌNG ĐỌC
        import datetime
        for i, audio_info in enumerate(dubbing_audio_files):
            if audio_info:
                idx = audio_info["index"]
                actual_duration = audio_info.get("actual_audio_duration", 0)
                # Cập nhật end time của đoạn sub tương ứng để nó biến mất NGAY khi đọc xong
                for seg in translated_segments:
                    if seg.index == idx and actual_duration > 0:
                        new_end = seg.start + datetime.timedelta(seconds=actual_duration + 0.1) # Thêm 0.1s cho tự nhiên
                        seg.end = new_end
                        break
                        
        # CHỐNG ĐÈ SUB (Anti-Overlap): Đảm bảo sub trước phải biến mất trước khi sub sau xuất hiện
        for i in range(len(translated_segments) - 1):
            if translated_segments[i].end > translated_segments[i+1].start:
                safe_end = translated_segments[i+1].start - datetime.timedelta(seconds=0.05)
                if safe_end > translated_segments[i].start:
                    translated_segments[i].end = safe_end
                else:
                    translated_segments[i].end = translated_segments[i].start + datetime.timedelta(seconds=0.1)
        
        # ===== BƯỚC 4.5: TẠO FILE ASS (CÓ SUB DỊCH ĐÃ ĐỒNG BỘ TIMING) =====
        ass_path = os.path.join(out_dir, "final.ass")
        await asyncio.to_thread(generate_ass_file, translated_segments, floating_segments, ass_path, play_res_x=vid_w, play_res_y=vid_h, main_y_pct=main_y_pct)
        sub_file_to_use = ass_path
        
        # Mix giọng tiếng Việt vào nền nhạc KHÔNG CÓ LỜI (no_vocals_audio)
        if shared_state.stop_requested: raise Exception("Bị hủy bởi lệnh /stop")
        await asyncio.to_thread(mix_audio_pydub, no_vocals_audio, dubbing_audio_files, mixed_audio, original_volume_db=-2, dubbing_volume_db=1)

        # ===== BƯỚC 6: XUẤT VIDEO =====
        await status_msg.edit_text(
            f"👀 *Quét chữ xong!*\n`{url}`\n\n"
            "🎬 *Bước 6/6:* Đang render video (NVENC)...\n"
            "⏳ Đây là bước cuối cùng...",
            parse_mode="Markdown"
        )
        # Lấy lại main_y_pct nếu có, nếu không thì dùng mặc định 88%
        y_pct = locals().get('main_y_pct', 0.88)
        if shared_state.stop_requested: raise Exception("Bị hủy bởi lệnh /stop")
        res = await asyncio.to_thread(process_video, video_path, sub_file_to_use, mixed_audio, final_video, main_y_pct=y_pct)
        if not res: raise Exception("Tiến trình render video bị lỗi hoặc đã bị hủy bằng lệnh /stop!")

        # ===== GỬI VIDEO =====
        await status_msg.edit_text(
            f"🎬 *Render xong!*\n`{url}`\n\n"
            "📤 Đang gửi video cho bạn...",
            parse_mode="Markdown"
        )

        caption_lines = [f"🎬 Video đã lồng tiếng Việt\n"]
        
        elapsed_time = int(time.time() - start_time)
        mins = elapsed_time // 60
        secs = elapsed_time % 60
        time_str = f"{mins} phút {secs} giây" if mins > 0 else f"{secs} giây"
        caption_lines.append(f"⏱️ Thời gian xử lý: {time_str}\n")
        
        remaining = global_queue.qsize()
        if remaining > 0:
            caption_lines.append(f"⏳ Phía sau còn {remaining} video đang chờ xử lý...\n")
        else:
            caption_lines.append(f"🎉 Đã hoàn tất toàn bộ hàng đợi!\n")
        
        caption_lines.append(f"📎 Link gốc: {url}\n")
        caption_lines.append(f"📝 Phụ đề ({len(translated_segments)} đoạn):\n")
        for seg in translated_segments[:10]:
            caption_lines.append(f"• {seg.content}")
        if len(translated_segments) > 10:
            caption_lines.append(f"\n... và {len(translated_segments) - 10} đoạn nữa")

        caption = "\n".join(caption_lines)
        if len(caption) > 1024:
            caption = caption[:1020] + "..."

        await send_video_safely(context, chat_id, final_video, caption, status_msg, url)

    except subprocess.TimeoutExpired:
        await status_msg.edit_text("❌ Tải video quá lâu (>5 phút). Thử link khác nhé!")
    except Exception as e:
        logger.error(f"Error processing {url}: {e}", exc_info=True)
        await status_msg.edit_text(f"❌ Lỗi xử lý:\n{str(e)[:500]}")


# ===== XỬ LÝ MESSAGE CÓ CHỨA LINK =====
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    # Tìm TẤT CẢ các URL trong tin nhắn bằng Regex
    urls = re.findall(r'(https?://[^\s]+)', text)

    if not urls:
        await update.message.reply_text(
            "❓ Hãy gửi link video (bắt đầu bằng http:// hoặc https://)\n"
            "Ví dụ: https://www.xiaohongshu.com/...\n"
            "💡 Mẹo: Bạn có thể gửi nhiều link cùng lúc để tải hàng loạt!"
        )
        return

    global queue_counter, worker_task
    import shared_state
    shared_state.stop_requested = False
    
    if worker_task is None or worker_task.done():
        worker_task = asyncio.create_task(video_worker())

    # Đưa từng URL vào hàng đợi
    for url in urls:
        queue_counter += 1
        await global_queue.put({
            'type': 'url',
            'pos': queue_counter,
            'update': update,
            'context': context,
            'url': url
        })
        
    await update.message.reply_text(
        f"✅ Đã thêm {len(urls)} link vào hàng đợi.\n"
        f"👉 Hàng đợi của bạn chạy từ thứ tự {queue_counter - len(urls) + 1} đến {queue_counter}.\n"
        f"⏳ Hiện tại có tổng cộng {global_queue.qsize()} video đang chờ Bot xử lý lần lượt 1-1.",
        parse_mode="Markdown"
    )


# ===== XỬ LÝ VIDEO GỬI TRỰC TIẾP =====
async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Người dùng gửi file video trực tiếp qua Telegram (Đẩy vào Queue)."""
    global queue_counter, worker_task
    import shared_state
    shared_state.stop_requested = False
    
    if worker_task is None or worker_task.done():
        worker_task = asyncio.create_task(video_worker())
        
    queue_counter += 1
    
    if update.message.video:
        file_obj = update.message.video
        filename = update.message.video.file_name or f"tg_video_{int(time.time())}.mp4"
    elif update.message.document:
        file_obj = update.message.document
        filename = update.message.document.file_name or f"tg_doc_{int(time.time())}.mp4"
    else:
        await update.message.reply_text("❌ Không nhận dạng được file video.")
        return
        
    await global_queue.put({
        'type': 'video',
        'pos': queue_counter,
        'update': update,
        'context': context,
        'file_id': file_obj.file_id,
        'filename': filename
    })
    
    remaining = global_queue.qsize()
    await update.message.reply_text(
        f"✅ Đã thêm video tải lên vào hàng đợi.\n"
        f"👉 Vị trí của bạn: #{queue_counter}.\n"
        f"⏳ Hiện tại có tổng cộng {remaining} video đang chờ Bot xử lý lần lượt 1-1.",
        parse_mode="Markdown"
    )

async def process_single_video(update: Update, context: ContextTypes.DEFAULT_TYPE, file_id: str, filename: str, pos: int):
    status_msg = await update.message.reply_text(
        f"▶️ *Đang xử lý Video tải lên (Thứ {pos} trong hàng đợi):*\n`{filename}`\n\n"
        f"⏳ Phía sau còn {global_queue.qsize()} video đang chờ...",
        parse_mode="Markdown"
    )

    try:
        file = await context.bot.get_file(file_id)
        download_dir = os.path.join(WORKSPACE, "downloads")
        os.makedirs(download_dir, exist_ok=True)
        
        # Thêm timestamp và uuid để tránh trùng lặp khi chạy hàng loạt
        import uuid
        uid = str(uuid.uuid4())[:8]
        safe_filename = f"{int(time.time())}_{uid}_{filename}"
        video_path = os.path.join(download_dir, safe_filename)

        await status_msg.edit_text("⏳ Đang tải video từ Telegram...")
        # Tăng timeout lên 600s để tránh lỗi Timed out khi tải file video lớn
        await file.download_to_drive(video_path, read_timeout=600, connect_timeout=600, pool_timeout=600, write_timeout=600)
        
        base_name = os.path.splitext(safe_filename)[0]
        out_dir = os.path.join(WORKSPACE, base_name)
        os.makedirs(out_dir, exist_ok=True)

        original_audio = os.path.join(out_dir, "original.wav")
        srt_original = os.path.join(out_dir, "original.srt")
        srt_translated = os.path.join(out_dir, "translated.srt")
        dubbing_dir = os.path.join(out_dir, "dubbing")
        mixed_audio = os.path.join(out_dir, "mixed.wav")
        final_video = os.path.join(out_dir, f"final_{base_name}.mp4")

        start_time = time.time()
        await status_msg.edit_text("🎧 Đang tách âm thanh...")
        import shared_state
        if shared_state.stop_requested: raise Exception("Bị hủy bởi lệnh /stop")
        await asyncio.to_thread(extract_audio_from_video, video_path, original_audio)

        # ===== BƯỚC 2.5: TÁCH VOCAL BẰNG DEMUCS =====
        await status_msg.edit_text("🎧 Đang tách giọng nhân vật khỏi nhạc nền (Demucs)...")
        from video_utils import separate_vocals_demucs
        if shared_state.stop_requested: raise Exception("Bị hủy bởi lệnh /stop")
        vocals_audio, no_vocals_audio = await asyncio.to_thread(separate_vocals_demucs, original_audio, out_dir)

        # ===== BƯỚC 3: NHẬN DẠNG GIỌNG NÓI =====
        await status_msg.edit_text("🤖 Whisper AI đang nhận dạng từ Vocal sạch...")
        if shared_state.stop_requested: raise Exception("Bị hủy bởi lệnh /stop")
        srt_segments = await asyncio.to_thread(extract_subtitles_whisper, vocals_audio, srt_original)

        # ===== BƯỚC 3.5: KIỂM TRA VỊ TRÍ PHỤ ĐỀ CHÍNH VÀ QUÉT PHỤ ĐỀ CÂM =====
        await status_msg.edit_text("👀 Đang quét vùng phụ đề cố định (OCR)...", parse_mode="Markdown")
        from ocr_utils import perform_video_ocr, extract_silent_subtitles_from_gaps
        from ass_utils import generate_ass_file
        try:
            if shared_state.stop_requested: raise Exception("Bị hủy bởi lệnh /stop")
            _, vid_w, vid_h, main_y_pct = await asyncio.to_thread(perform_video_ocr, video_path, target_lang="vi", sample_rate=1.0, api_key=GEMINI_API_KEY, srt_segments=srt_segments)
            
            floating_segments = []
            
            import datetime
            for i in range(len(srt_segments) - 1):
                if srt_segments[i].end > srt_segments[i+1].start:
                    new_end = srt_segments[i+1].start - datetime.timedelta(seconds=0.05)
                    if new_end > srt_segments[i].start:
                        srt_segments[i].end = new_end
                    else:
                        srt_segments[i].end = srt_segments[i].start + datetime.timedelta(seconds=0.1)

            for i, seg in enumerate(srt_segments, 1):
                seg.index = i
        except Exception as e:
            logger.error(f"OCR Error: {e}", exc_info=True)
            vid_w, vid_h, main_y_pct, floating_segments = 1920, 1080, 0.88, []

        # ===== BƯỚC 4: DỊCH PHỤ ĐỀ =====
        await status_msg.edit_text(f"🌐 Đang dịch {len(srt_segments)} đoạn phụ đề (Có hỗ trợ AI Vision)...")
        if shared_state.stop_requested: raise Exception("Bị hủy bởi lệnh /stop")
        translated_segments = await asyncio.to_thread(translate_subtitles, srt_segments, "vi", api_key=GEMINI_API_KEY, video_path=video_path)
        await asyncio.to_thread(save_srt, translated_segments, srt_translated)

        # (Di chuyển BƯỚC 4.5 xuống dưới BƯỚC 5)

        # ===== BƯỚC 5: LỒNG TIẾNG =====
        await status_msg.edit_text("🗣️ Đang lồng tiếng AI (Giọng Hoài My)...")
        if shared_state.stop_requested: raise Exception("Bị hủy bởi lệnh /stop")
        # Khôi phục giọng RVC (Đáng yêu)
        rvc_model_path = None
        models_dir = os.path.join(WORKSPACE, "models", "rvc")
        if os.path.exists(models_dir):
            for f in os.listdir(models_dir):
                if f.endswith(".pth"):
                    rvc_model_path = os.path.join(models_dir, f)
                    break
                    
        v_source = "rvc" if rvc_model_path else "edge"
        if rvc_model_path:
            v_param = rvc_model_path
        else:
            # from audio_analysis import detect_gender
            # gender = detect_gender(vocals_audio)
            # v_param = "vi-VN-HoaiMyNeural" if gender == "female" else "vi-VN-NamMinhNeural"
            v_param = "vi-VN-HoaiMyNeural"  # Tạm thời cố định giọng nữ
        
        dubbing_audio_files = await generate_dubbing_audio(
            translated_segments, dubbing_dir, voice_source=v_source, voice_param=v_param
        )
        
        # ĐỒNG BỘ THỜI GIAN BIẾN MẤT CỦA PHỤ ĐỀ THEO GIỌNG ĐỌC
        import datetime
        for i, audio_info in enumerate(dubbing_audio_files):
            if audio_info:
                idx = audio_info["index"]
                actual_duration = audio_info.get("actual_audio_duration", 0)
                for seg in translated_segments:
                    if seg.index == idx and actual_duration > 0:
                        new_end = seg.start + datetime.timedelta(seconds=actual_duration + 0.1)
                        seg.end = new_end
                        break

        # CHỐNG ĐÈ SUB (Anti-Overlap): Đảm bảo sub trước phải biến mất trước khi sub sau xuất hiện
        for i in range(len(translated_segments) - 1):
            if translated_segments[i].end > translated_segments[i+1].start:
                safe_end = translated_segments[i+1].start - datetime.timedelta(seconds=0.05)
                if safe_end > translated_segments[i].start:
                    translated_segments[i].end = safe_end
                else:
                    translated_segments[i].end = translated_segments[i].start + datetime.timedelta(seconds=0.1)

        # ===== BƯỚC 4.5: TẠO FILE ASS (CÓ SUB DỊCH ĐÃ ĐỒNG BỘ TIMING) =====
        ass_path = os.path.join(out_dir, "final.ass")
        await asyncio.to_thread(generate_ass_file, translated_segments, floating_segments, ass_path, play_res_x=vid_w, play_res_y=vid_h, main_y_pct=main_y_pct)
        sub_file_to_use = ass_path

        if shared_state.stop_requested: raise Exception("Bị hủy bởi lệnh /stop")
        await asyncio.to_thread(mix_audio_pydub, no_vocals_audio, dubbing_audio_files, mixed_audio, original_volume_db=-2, dubbing_volume_db=1)

        # ===== BƯỚC 6: XUẤT VIDEO =====
        await status_msg.edit_text("🎬 Đang render video (NVENC)...")
        y_pct = locals().get('main_y_pct', 0.88)
        if shared_state.stop_requested: raise Exception("Bị hủy bởi lệnh /stop")
        res = await asyncio.to_thread(process_video, video_path, sub_file_to_use, mixed_audio, final_video, main_y_pct=y_pct)
        if not res: raise Exception("Tiến trình render video bị lỗi hoặc đã bị hủy bằng lệnh /stop!")

        await status_msg.edit_text("📤 Đang gửi video...")
        
        elapsed_time = int(time.time() - start_time)
        mins = elapsed_time // 60
        secs = elapsed_time % 60
        time_str = f"{mins} phút {secs} giây" if mins > 0 else f"{secs} giây"
        remaining = global_queue.qsize()
        queue_status = f"\n⏳ Phía sau còn {remaining} video đang chờ xử lý..." if remaining > 0 else "\n🎉 Đã hoàn tất toàn bộ hàng đợi!"
        caption = f"✅ Video đã lồng tiếng Tiếng Việt!\n⏱️ Thời gian xử lý: {time_str}{queue_status}"
        
        with open(final_video, 'rb') as vf:
            pass # (Giữ block open để tương thích nếu cần)
            
        await send_video_safely(context, update.message.chat_id, final_video, caption, status_msg, filename)

    except Exception as e:
        logger.error(f"Error processing video: {e}", exc_info=True)
        await status_msg.edit_text(f"❌ Lỗi: {str(e)[:500]}")


# ===== KHỞI CHẠY BOT =====
def main():
    if BOT_TOKEN == "PASTE_YOUR_TOKEN_HERE":
        print("=" * 60)
        print("❌ LỖI: Chưa cấu hình Bot Token!")
        print("Mở file telegram_bot.py và dán Token vào dòng BOT_TOKEN")
        print("Lấy Token từ @BotFather trên Telegram")
        print("=" * 60)
        return
    print("Dang khoi dong Telegram Bot...")
    print(f"Workspace: {WORKSPACE}")

    from telegram.request import HTTPXRequest
    # Tăng timeout lên 120 giây để không bị Timed out khi gửi/tải video lớn
    request = HTTPXRequest(
        connect_timeout=30,
        read_timeout=120,
        write_timeout=120,
        pool_timeout=120,
    )
    app = Application.builder().token(BOT_TOKEN).request(request).build()

    # Đăng ký handlers
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("stop", cmd_stop))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(MessageHandler(filters.VIDEO | filters.Document.VIDEO, handle_video))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Bot da san sang! Dang lang nghe tin nhan...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()

