import cv2
import easyocr
import os
import srt
import sys
import numpy as np

sys.path.insert(0, '.')
from ass_utils import generate_ass_file
from video_utils import process_video

# 1. Test OCR across 0.15 -> 0.92
video_input = r"C:\Users\admin\.gemini\antigravity\scratch\video-dubbing-app\workspace\downloads\1787311966_16018c93_6小卡分格收纳盒.mp4"
mixed_audio = r"C:\Users\admin\.gemini\antigravity\scratch\video-dubbing-app\workspace\1787311966_16018c93_6小卡分格收纳盒\mixed.wav"
srt_path = r"C:\Users\admin\.gemini\antigravity\scratch\video-dubbing-app\workspace\1787311966_16018c93_6小卡分格收纳盒\translated.srt"

with open(srt_path, "r", encoding="utf-8") as f:
    translated_segments = list(srt.parse(f.read()))

# 2. Set the detected top/bottom Y coordinates from full scan
# Segment 0 (0:00 - 0:02.14) has text at Y = 0.302 - 0.340
# Segment 1+ have text at Y = 0.263 - 0.298
for i, seg in enumerate(translated_segments):
    if i == 0:
        seg.y_pct = 0.302
        seg.max_y_pct = 0.340
    else:
        seg.y_pct = 0.263
        seg.max_y_pct = 0.298
    seg.best_block = None

# 3. Generate ASS
clean_ass = r"C:\Users\admin\.gemini\antigravity\scratch\video-dubbing-app\workspace\1787311966_16018c93_6小卡分格收纳盒\clean_top_sub.ass"
generate_ass_file(translated_segments, [], clean_ass, play_res_x=720, play_res_y=1280, main_y_pct=0.302)

# 4. Render
clean_output = r"C:\Users\admin\.gemini\antigravity\scratch\video-dubbing-app\backend\test_card_box_clean.mp4"
ok = process_video(video_input, clean_ass, mixed_audio, clean_output, main_y_pct=0.302, delogo=True)
print("Render status:", ok)

# 5. Extract frame at 1s and 4s
cap = cv2.VideoCapture(clean_output)
cap.set(cv2.CAP_PROP_POS_MSEC, 1000)
ret, f1 = cap.read()
if ret: cv2.imwrite("frame_cardbox_1s.jpg", f1)

cap.set(cv2.CAP_PROP_POS_MSEC, 4000)
ret, f2 = cap.read()
if ret: cv2.imwrite("frame_cardbox_4s.jpg", f2)
cap.release()

print("Card box test render complete!")
