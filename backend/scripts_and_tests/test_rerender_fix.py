import cv2
import os
import srt
import sys
import shutil

sys.path.insert(0, '.')
from ass_utils import generate_ass_file
from video_utils import process_video

# 1. Load translated segments
srt_path = r"C:\Users\admin\.gemini\antigravity\scratch\video-dubbing-app\workspace\1787306557_251c4c13_不看尺寸的下场\translated.srt"
with open(srt_path, "r", encoding="utf-8") as f:
    translated_segments = list(srt.parse(f.read()))

# 2. Set clean global subtitle Y to all segments (Top=0.713, Bottom=0.742)
for seg in translated_segments:
    seg.y_pct = 0.713
    seg.max_y_pct = 0.742
    seg.best_block = None

# 3. Generate clean ASS with ascii filename
clean_ass_path = r"C:\Users\admin\.gemini\antigravity\scratch\video-dubbing-app\backend\clean_test.ass"
generate_ass_file(translated_segments, [], clean_ass_path, play_res_x=720, play_res_y=1280, main_y_pct=0.713)

# 4. Render test video
video_input = r"C:\Users\admin\.gemini\antigravity\scratch\video-dubbing-app\workspace\downloads\1787306557_251c4c13_不看尺寸的下场.mp4"
mixed_audio = r"C:\Users\admin\.gemini\antigravity\scratch\video-dubbing-app\workspace\1787306557_251c4c13_不看尺寸的下场\mixed.wav"
clean_output = r"C:\Users\admin\.gemini\antigravity\scratch\video-dubbing-app\backend\test_clean_sub_covered.mp4"

ok = process_video(video_input, clean_ass_path, mixed_audio, clean_output, main_y_pct=0.713, delogo=True)
print("Render result:", ok)

# 5. Extract frame at 1s and 2s
cap = cv2.VideoCapture(clean_output)
cap.set(cv2.CAP_PROP_POS_MSEC, 1000)
ret, frame1 = cap.read()
if ret: cv2.imwrite("frame_fixed_1s.jpg", frame1)

cap.set(cv2.CAP_PROP_POS_MSEC, 2500)
ret, frame2 = cap.read()
if ret: cv2.imwrite("frame_fixed_2.5s.jpg", frame2)
cap.release()

print("Re-render test complete!")
