import asyncio
import logging
logging.basicConfig(level=logging.INFO)
from ocr_utils import perform_video_ocr, extract_silent_subtitles_from_gaps

async def main():
    video_path = 'downloads/test_video.mp4'
    print("Testing perform_video_ocr...")
    srt_segs, w, h, main_y = await asyncio.to_thread(perform_video_ocr, video_path, 'vi', 0.25, '', [])
    print(f"Main Y: {main_y}, W: {w}, H: {h}")
    
    print("Testing extract_silent_subtitles_from_gaps...")
    gap_segs = extract_silent_subtitles_from_gaps(video_path, [], main_y, h)
    with open("gaps.txt", "w", encoding="utf-8") as f:
        for seg in gap_segs:
            f.write(f'Gap segment: {seg.start} -> {seg.end}: {seg.content}\n')

if __name__ == '__main__':
    asyncio.run(main())
