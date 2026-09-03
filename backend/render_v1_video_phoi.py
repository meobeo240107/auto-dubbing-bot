import asyncio
import os
import sys
from pathlib import Path

# Fix Windows console UTF-8 encoding
if hasattr(sys.stdout, "reconfigure"):
    try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass
if hasattr(sys.stderr, "reconfigure"):
    try: sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

# Force Tool V1 legacy mode
os.environ["PIPELINE_MODE"] = "legacy"

from batch_processor import process_single_local_video

async def main():
    input_dir = Path(r"D:\video phôi")
    output_dir = Path(r"D:\banve")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    video_files = []
    for f in sorted(input_dir.glob("*.mp4")):
        if " (1)" in f.name:
            continue
        video_files.append(f)
        
    print(f"🎬 [Tool V1] Tìm thấy {len(video_files)} video trong {input_dir}:", flush=True)
    for vf in video_files:
        print(f" - {vf.name}", flush=True)
        
    for vf in video_files:
        dest_check = list(output_dir.glob(f"*{vf.stem}*.mp4"))
        if dest_check:
            print(f"\n⏩ Video {vf.name} đã được render tại {dest_check[0].name}. Tiếp tục video tiếp theo...", flush=True)
            continue
            
        print(f"\n==========================================", flush=True)
        print(f"🚀 [Tool V1] Bắt đầu xử lý: {vf.name}", flush=True)
        print(f"==========================================", flush=True)
        
        async def progress(msg):
            print(f"⏱️ [Tool V1] {msg}", flush=True)
            
        success = await process_single_local_video(str(vf), str(output_dir), progress)
        if success:
            print(f"🎉 [Tool V1] HOÀN TẤT THÀNH CÔNG: {vf.name} -> {output_dir}", flush=True)
        else:
            print(f"❌ [Tool V1] Xử lý thất bại: {vf.name}", flush=True)

if __name__ == "__main__":
    asyncio.run(main())
