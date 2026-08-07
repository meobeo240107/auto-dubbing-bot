import asyncio
import os
import datetime
from ocr_utils import perform_video_ocr

async def main():
    print("===== TEST 1: 6gXdwMvCOQ7 =====")
    video_path1 = "workspace/downloads/test_bug_vid1.mp4"
    if not os.path.exists(video_path1):
        os.system(r"venv\Scripts\yt-dlp.exe -o workspace/downloads/test_bug_vid1.mp4 http://xhslink.com/o/6gXdwMvCOQ7")
    class MockSegment:
        def __init__(self, c):
            self.content = c
            self.start = datetime.timedelta(seconds=0)
            self.end = datetime.timedelta(seconds=4)
    srt_segments1 = [MockSegment("这次做的是遇光变色的缤纷糖果色调")]
    blocks1, _, _, main_y_pct1 = perform_video_ocr(video_path1, target_lang="vi", sample_rate=1.0, api_key="", srt_segments=srt_segments1)
    print(f"MAIN Y PCT 1: {main_y_pct1}")
    for seg in srt_segments1:
        print(f"[{seg.start} - {seg.end}] {seg.content}")
        print(f"   y_pct: {getattr(seg, 'y_pct', 'None')}, max_y_pct: {getattr(seg, 'max_y_pct', 'None')}")

    print("\n===== TEST 2: 6BlzlHbKmpi =====")
    video_path2 = "workspace/downloads/test_bug_vid2.mp4"
    if not os.path.exists(video_path2):
        os.system(r"venv\Scripts\yt-dlp.exe -o workspace/downloads/test_bug_vid2.mp4 http://xhslink.com/o/6BlzlHbKmpi")
    srt_segments2 = [MockSegment("那就盖一栋")]
    blocks2, _, _, main_y_pct2 = perform_video_ocr(video_path2, target_lang="vi", sample_rate=1.0, api_key="", srt_segments=srt_segments2)
    print(f"MAIN Y PCT 2: {main_y_pct2}")
    for seg in srt_segments2:
        print(f"[{seg.start} - {seg.end}] {seg.content}")
        print(f"   y_pct: {getattr(seg, 'y_pct', 'None')}, max_y_pct: {getattr(seg, 'max_y_pct', 'None')}")

asyncio.run(main())
