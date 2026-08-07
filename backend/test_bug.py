import asyncio
import os
import datetime
from ocr_utils import perform_video_ocr

async def main():
    video_path = "workspace/downloads/test_bug.mp4"
    if not os.path.exists(video_path):
        os.system(r"venv\Scripts\yt-dlp.exe -o workspace/downloads/test_bug.mp4 http://xhslink.com/o/8RmtGBHR0cM")
    
    print("Video downloaded, running OCR...")
    class MockSegment:
        def __init__(self, c):
            self.content = c
            self.start = datetime.timedelta(seconds=0)
            self.end = datetime.timedelta(seconds=5)
    srt_segments = [MockSegment("Dòng kẹo dẻo Tango đã chính thức lên kệ mùa hè này rồi")]
    blocks, w, h, main_y_pct = perform_video_ocr(video_path, target_lang="vi", sample_rate=1.0, api_key="", srt_segments=srt_segments)
    
    print(f"MAIN Y PCT: {main_y_pct}")

asyncio.run(main())
