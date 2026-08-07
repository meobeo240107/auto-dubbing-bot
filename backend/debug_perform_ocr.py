import asyncio
from ocr_utils import perform_video_ocr
import datetime

class MockSeg:
    def __init__(self, start, end, text):
        self.start = start
        self.end = end
        self.content = text
        self.index = 1

async def main():
    segs = [MockSeg(datetime.timedelta(seconds=2.84), datetime.timedelta(seconds=4.54), '头发往天上飞的又叫什么?')]
    y = await perform_video_ocr('workspace/downloads/test_bug_vid3.mp4', segs, 1.0)
    print(f'MAIN_Y_PCT: {y}')
    for s in segs:
        print(f'SEG Y: {getattr(s, "y_pct", None)} BEST_BLOCK: {getattr(s, "best_block", None)}')

asyncio.run(main())
