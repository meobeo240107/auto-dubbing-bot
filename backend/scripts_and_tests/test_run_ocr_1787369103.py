import os
import srt
import sys

sys.stdout.reconfigure(encoding='utf-8')

sys.path.insert(0, '.')
from ocr_utils import perform_video_ocr

video_input = r"C:\Users\admin\.gemini\antigravity\scratch\video-dubbing-app\workspace\downloads\1787369103_2849592d_难道没有人发现它是一个防偷卡神器吗小卡打包话题_出卡打包话题_打包胶带话题.mp4"
srt_path = r"C:\Users\admin\.gemini\antigravity\scratch\video-dubbing-app\workspace\1787369103_2849592d_难道没有人发现它是一个防偷卡神器吗小卡打包话题_出卡打包话题_打包胶带话题\original.srt"

with open(srt_path, "r", encoding="utf-8") as f:
    srt_segments = list(srt.parse(f.read()))

_, width, height, main_y_pct = perform_video_ocr(video_input, srt_segments=srt_segments)

print(f"\nFinal OCR Result: Width={width}, Height={height}, Main_Y_Pct={main_y_pct:.3f}")
for i, seg in enumerate(srt_segments):
    print(f"Seg {i} [{seg.start.total_seconds():.1f}s - {seg.end.total_seconds():.1f}s]: Y: {seg.y_pct:.3f} - {seg.max_y_pct:.3f}")
