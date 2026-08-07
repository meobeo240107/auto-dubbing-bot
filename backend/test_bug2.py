import asyncio
import os
from ocr_utils import perform_video_ocr

async def main():
    video_path = "workspace/downloads/test_bug2.mp4"
    if not os.path.exists(video_path):
        os.system(r"venv\Scripts\yt-dlp.exe -o workspace/downloads/test_bug2.mp4 http://xhslink.com/o/6gXdwMvCOQ7")
    
    print("Video downloaded, running OCR...")
    class MockSegment:
        def __init__(self, c):
            self.content = c
            self.start = 0
            self.end = 1
    srt_segments = [] # Pass empty to see the fallback Y or we can extract real SRT first, but let's just see the blocks.
    blocks, w, h, main_y_pct = perform_video_ocr(video_path, target_lang="vi", sample_rate=1.0, api_key="", srt_segments=srt_segments)
    
    print(f"MAIN Y PCT: {main_y_pct}")

asyncio.run(main())
