import os
import srt
import sys
import re
import numpy as np

sys.path.insert(0, '.')
from ass_utils import generate_ass_file
from video_utils import process_video

# 1. Load translated segments
srt_path = r"C:\Users\admin\.gemini\antigravity\scratch\video-dubbing-app\workspace\1787369103_2849592d_难道没有人发现它是一个防偷卡神器吗小卡打包话题_出卡打包话题_打包胶带话题\translated.srt"
with open(srt_path, "r", encoding="utf-8") as f:
    translated_segments = list(srt.parse(f.read()))

# 2. Set the clean global subtitle Y to all segments (Top=0.704, Bottom=0.739)
for seg in translated_segments:
    seg.y_pct = 0.704
    seg.max_y_pct = 0.739
    seg.best_block = None

# 3. Generate clean ASS
clean_ass = r"C:\Users\admin\.gemini\antigravity\scratch\video-dubbing-app\workspace\1787369103_2849592d_难道没有人发现它是一个防偷卡神器吗小卡打包话题_出卡打包话题_打包胶带话题\clean_fixed.ass"
generate_ass_file(translated_segments, [], clean_ass, play_res_x=720, play_res_y=1280, main_y_pct=0.704)

# 4. Render
video_input = r"C:\Users\admin\.gemini\antigravity\scratch\video-dubbing-app\workspace\downloads\1787369103_2849592d_难道没有人发现它是一个防偷卡神器吗小卡打包话题_出卡打包话题_打包胶带话题.mp4"
mixed_audio = r"C:\Users\admin\.gemini\antigravity\scratch\video-dubbing-app\workspace\1787369103_2849592d_难道没有人发现它是一个防偷卡神器吗小卡打包话题_出卡打包话题_打包胶带话题\mixed.wav"
clean_output = r"C:\Users\admin\.gemini\antigravity\scratch\video-dubbing-app\backend\test_anti_theft_clean.mp4"

ok = process_video(video_input, clean_ass, mixed_audio, clean_output, main_y_pct=0.704, delogo=True)
print("Render status:", ok)

# 5. Extract frame at 5.5s (The user's screenshot moment!)
import cv2
cap = cv2.VideoCapture(clean_output)
cap.set(cv2.CAP_PROP_POS_MSEC, 5500)
ret, f1 = cap.read()
if ret: cv2.imwrite("frame_fixed_5.5s.jpg", f1)
cap.release()

print("Test render complete!")
