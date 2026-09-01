import os
import srt
from datetime import timedelta
from faster_whisper import WhisperModel

def extract_subtitles_whisper(audio_path, output_srt_path, num_workers=2):
    print(f"Transcribing {audio_path} with Faster-Whisper Large-v3...")
    import torch, gc
    num_threads = max((os.cpu_count() or 4) - 1, 2)
    worker_count = max(1, int(num_workers))
    
    if torch.cuda.is_available():
        print(f"🚀 CUDA detected: {torch.cuda.get_device_name(0)}. Loading Whisper Large-v3...")
        model = WhisperModel(
            "large-v3",
            device="cuda",
            compute_type="int8_float16",
            num_workers=worker_count,
        )
    else:
        print(f"⚡ Loading Whisper Large-v3 on CPU ({num_threads} threads)...")
        model = WhisperModel("large-v3", device="cpu", compute_type="int8", cpu_threads=num_threads)
        
    try:
        segments, info = model.transcribe(
            audio_path, 
            beam_size=5, 
            vad_filter=True, 
            vad_parameters=dict(min_silence_duration_ms=600, threshold=0.4),
            condition_on_previous_text=False,
            temperature=[0.0, 0.2, 0.4]
        )
        
        merged_segments = []
        current_segment = None
        
        for segment in segments:
            text = segment.text.strip()
            if not text:
                continue
                
            if current_segment is None:
                current_segment = {
                    "start": segment.start,
                    "end": segment.end,
                    "text": text
                }
            else:
                gap = segment.start - current_segment["end"]
                duration = segment.end - current_segment["start"]
                
                if gap < 0.5 and duration < 3.0:
                    current_segment["end"] = segment.end
                    current_segment["text"] += " " + text
                else:
                    merged_segments.append(current_segment)
                    current_segment = {
                        "start": segment.start,
                        "end": segment.end,
                        "text": text
                    }
                    
        if current_segment is not None:
            merged_segments.append(current_segment)
        
        srt_segments = []
        for i, seg in enumerate(merged_segments, start=1):
            sub = srt.Subtitle(
                index=i,
                start=timedelta(seconds=seg["start"]),
                end=timedelta(seconds=seg["end"]),
                content=seg["text"].strip()
            )
            srt_segments.append(sub)
        
        with open(output_srt_path, "w", encoding="utf-8") as f:
            f.write(srt.compose(srt_segments))
        
        return srt_segments
    finally:
        del model
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        print("🧹 Đã giải phóng bộ nhớ RAM/VRAM của Whisper AI.")

def save_srt(srt_segments, output_path):
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(srt.compose(srt_segments, reindex=False))
