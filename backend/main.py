from fastapi import FastAPI, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import os
import asyncio
from pathlib import Path

from ai.transcription import extract_subtitles_whisper, save_srt
from ai.translation import translate_subtitles
from ai.voice_cloning import generate_dubbing_audio
from video_utils import extract_audio_from_video, mix_audio_pydub, process_video

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).resolve().parent
WORKSPACE = os.getenv("AUTODUB_WORKSPACE", str(BASE_DIR.parent / "workspace"))
OUTPUT_DIR = os.getenv("AUTODUB_OUTPUT_DIR", r"D:\banve")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
os.makedirs(WORKSPACE, exist_ok=True)

@app.get("/api/logs")
async def api_get_logs():
    """Trả về 100 dòng log mới nhất của bot."""
    log_file = str(BASE_DIR / "app.log")
    if not os.path.exists(log_file):
        return {"logs": "Chưa có log nào."}
    
    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            # Lấy 100 dòng cuối để không bị quá nặng
            return {"logs": "".join(lines[-100:])}
    except Exception as e:
        return {"logs": f"Lỗi khi đọc log: {e}"}

# ===== API: Tạo phụ đề (Transcribe + Translate) =====
@app.post("/api/generate_subtitles")
async def api_generate_subtitles(video_path: str = Form(...), target_lang: str = Form("vi")):
    """Nhận đường dẫn file video trên máy, tạo phụ đề gốc và dịch."""
    try:
        base_name = os.path.splitext(os.path.basename(video_path))[0]
        out_dir = os.path.join(WORKSPACE, base_name)
        os.makedirs(out_dir, exist_ok=True)

        original_audio = os.path.join(out_dir, "original.wav")
        srt_original = os.path.join(out_dir, "original.srt")
        srt_translated = os.path.join(out_dir, "translated.srt")

        # 1. Extract audio
        extract_audio_from_video(video_path, original_audio)

        # 2. Transcribe with Whisper
        srt_segments = extract_subtitles_whisper(original_audio, srt_original)

        # 3. Translate
        translated_segments = translate_subtitles(
            srt_segments,
            target_lang,
            api_key=GEMINI_API_KEY,
            video_path=video_path,
        )
        save_srt(translated_segments, srt_translated)

        # Prepare response data
        subtitles = []
        for seg in translated_segments:
            subtitles.append({
                "index": seg.index,
                "start": seg.start.total_seconds(),
                "end": seg.end.total_seconds(),
                "content": seg.content
            })

        return {
            "status": "success",
            "original_srt": srt_original,
            "translated_srt": srt_translated,
            "subtitles": subtitles,
            "total": len(subtitles)
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"status": "error", "message": str(e)}


# ===== API: Xử lý full (Lồng tiếng + Xuất video) =====
@app.post("/api/process_video")
async def api_process_video(
    video_path: str = Form(...),
    target_lang: str = Form("vi"),
    voice_source: str = Form("edge"),
    voice_param: str = Form("vi-VN-HoaiMyNeural"),
    api_key: str = Form(""),
    font_name: str = Form("Arial"),
    font_color: str = Form("&H00FFFFFF"),
    font_weight: int = Form(1)
):
    """Xử lý full: Transcribe → Dịch → TTS → Mix Audio → Blur + Sub → Xuất video."""
    try:
        base_name = os.path.splitext(os.path.basename(video_path))[0]
        out_dir = os.path.join(WORKSPACE, base_name)
        os.makedirs(out_dir, exist_ok=True)

        original_audio = os.path.join(out_dir, "original.wav")
        srt_original = os.path.join(out_dir, "original.srt")
        srt_translated = os.path.join(out_dir, "translated.srt")
        dubbing_dir = os.path.join(out_dir, "dubbing")
        mixed_audio = os.path.join(out_dir, "mixed.wav")
        final_video = os.path.join(out_dir, f"final_{base_name}.mp4")

        # 1. Extract audio
        extract_audio_from_video(video_path, original_audio)

        # 2. Transcribe
        srt_segments = extract_subtitles_whisper(original_audio, srt_original)

        # 3. Translate
        translated_segments = translate_subtitles(
            srt_segments,
            target_lang,
            api_key=api_key or GEMINI_API_KEY,
            video_path=video_path,
        )
        save_srt(translated_segments, srt_translated)

        # 4. Generate TTS dubbing
        dubbing_audio_files = await generate_dubbing_audio(
            translated_segments, dubbing_dir,
            voice_source=voice_source,
            voice_param=voice_param,
            api_key=api_key
        )

        # 5. Mix audio (original + dubbing)
        mix_audio_pydub(original_audio, dubbing_audio_files, mixed_audio)

        # 6. Final render: Blur + Subtitles + Audio → Output video
        rendered = process_video(
            video_path,
            srt_translated,
            mixed_audio,
            final_video,
            font_name=font_name,
            font_color=font_color,
            font_weight=font_weight,
        )
        if not rendered:
            raise RuntimeError("Final video render failed")
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        published_video = os.path.join(OUTPUT_DIR, f"Dubbed_{base_name}.mp4")
        from pipeline_v2.atomic_io import atomic_copy_file

        atomic_copy_file(final_video, published_video)

        return {
            "status": "success",
            "final_video": published_video,
            "message": f"Xuất video thành công: {published_video}"
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"status": "error", "message": str(e)}


# ===== API: Tải video đã xuất =====
@app.get("/api/download/{filename}")
async def download_video(filename: str):
    """Tải file video đã render xong."""
    # Search in workspace subdirectories
    for root, dirs, files in os.walk(WORKSPACE):
        if filename in files:
            return FileResponse(os.path.join(root, filename), media_type="video/mp4", filename=filename)
    return {"status": "error", "message": "File not found"}


# ===== API: Tải video từ URL + Xử lý tự động =====
@app.post("/api/process_url")
async def api_process_url(
    url: str = Form(...),
    target_lang: str = Form("vi"),
    voice_source: str = Form("edge"),
    voice_param: str = Form("vi-VN-HoaiMyNeural"),
    api_key: str = Form(""),
    font_name: str = Form("Arial"),
    font_color: str = Form("&H00FFFFFF"),
    font_weight: int = Form(1)
):
    """Tải video từ URL (Xiaohongshu, TikTok, YouTube...) rồi xử lý toàn bộ."""
    import time

    download_dir = os.path.join(WORKSPACE, "downloads")
    os.makedirs(download_dir, exist_ok=True)

    # Tạo tên file duy nhất
    timestamp = str(int(time.time()))
    try:
        # Use the shared no-watermark downloader, including 206 + ffprobe checks.
        from social_downloader import download_social_video

        success, video_path, _title, download_error = await asyncio.to_thread(
            download_social_video, url, download_dir, timestamp
        )
        if not success:
            return {
                "status": "error",
                "step": "download",
                "message": download_error or "Không thể tải video.",
            }
        video_filename = os.path.basename(video_path)
        base_name = os.path.splitext(video_filename)[0]

        # 2. Xử lý pipeline (giống process_video)
        out_dir = os.path.join(WORKSPACE, base_name)
        os.makedirs(out_dir, exist_ok=True)

        original_audio = os.path.join(out_dir, "original.wav")
        srt_original = os.path.join(out_dir, "original.srt")
        srt_translated = os.path.join(out_dir, "translated.srt")
        dubbing_dir = os.path.join(out_dir, "dubbing")
        mixed_audio = os.path.join(out_dir, "mixed.wav")
        final_video = os.path.join(out_dir, f"final_{base_name}.mp4")

        # Extract audio
        extract_audio_from_video(video_path, original_audio)

        # Transcribe
        srt_segments = extract_subtitles_whisper(original_audio, srt_original)

        # Translate
        translated_segments = translate_subtitles(
            srt_segments,
            target_lang,
            api_key=api_key or GEMINI_API_KEY,
            video_path=video_path,
        )
        save_srt(translated_segments, srt_translated)

        # Subtitles for response
        subtitles = []
        for seg in translated_segments:
            subtitles.append({
                "index": seg.index,
                "start": seg.start.total_seconds(),
                "end": seg.end.total_seconds(),
                "content": seg.content
            })

        # TTS
        dubbing_audio_files = await generate_dubbing_audio(
            translated_segments, dubbing_dir,
            voice_source=voice_source,
            voice_param=voice_param,
            api_key=api_key
        )

        # Mix audio
        mix_audio_pydub(original_audio, dubbing_audio_files, mixed_audio)

        # Final render
        rendered = process_video(
            video_path,
            srt_translated,
            mixed_audio,
            final_video,
            font_name=font_name,
            font_color=font_color,
            font_weight=font_weight,
        )
        if not rendered:
            raise RuntimeError("Final video render failed")
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        published_video = os.path.join(OUTPUT_DIR, f"Dubbed_{base_name}.mp4")
        from pipeline_v2.atomic_io import atomic_copy_file

        atomic_copy_file(final_video, published_video)

        return {
            "status": "success",
            "downloaded_video": video_path,
            "final_video": published_video,
            "subtitles": subtitles,
            "message": f"Hoàn tất! Video đã xuất tại: {published_video}"
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"status": "error", "step": "process", "message": str(e)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
