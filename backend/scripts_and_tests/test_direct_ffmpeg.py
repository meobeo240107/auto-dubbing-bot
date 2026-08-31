import cv2
import os
import srt
import sys
import subprocess

sys.path.insert(0, '.')
from ass_utils import generate_ass_file

# 1. Load translated segments
srt_path = r"C:\Users\admin\.gemini\antigravity\scratch\video-dubbing-app\workspace\1787306557_251c4c13_不看尺寸的下场\translated.srt"
with open(srt_path, "r", encoding="utf-8") as f:
    translated_segments = list(srt.parse(f.read()))

# 2. Set clean global subtitle Y to all segments (Top=0.713, Bottom=0.742)
for seg in translated_segments:
    seg.y_pct = 0.713
    seg.max_y_pct = 0.742
    seg.best_block = None

# 3. Generate clean ASS
clean_ass_path = r"C:\Users\admin\.gemini\antigravity\scratch\video-dubbing-app\workspace\1787306557_251c4c13_不看尺寸的下场\clean_fixed.ass"
generate_ass_file(translated_segments, [], clean_ass_path, play_res_x=720, play_res_y=1280, main_y_pct=0.713)

# 4. Render with clean paths
video_input = r"C:\Users\admin\.gemini\antigravity\scratch\video-dubbing-app\workspace\downloads\1787306557_251c4c13_不看尺寸的下场.mp4"
mixed_audio = r"C:\Users\admin\.gemini\antigravity\scratch\video-dubbing-app\workspace\1787306557_251c4c13_不看尺寸的下场\mixed.wav"
clean_output = r"C:\Users\admin\.gemini\antigravity\scratch\video-dubbing-app\backend\test_clean_sub_covered.mp4"

# Safe Windows short path / escaped path for FFmpeg subtitles
ass_escaped = clean_ass_path.replace('\\', '/').replace(':', '\\:')
vf_str = f"subtitles='{ass_escaped}'"

cmd = [
    'ffmpeg', '-y',
    '-i', video_input,
    '-i', mixed_audio,
    '-vf', vf_str,
    '-map', '0:v',
    '-map', '1:a',
    '-c:v', 'h264_nvenc', '-preset', 'fast',
    '-pix_fmt', 'yuv420p',
    '-c:a', 'aac', '-b:a', '192k',
    '-movflags', '+faststart',
    '-shortest',
    clean_output
]

res = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
print("FFmpeg exit code:", res.returncode)
if res.returncode != 0:
    print("FFmpeg stderr:", res.stderr[-500:])

cap = cv2.VideoCapture(clean_output)
cap.set(cv2.CAP_PROP_POS_MSEC, 1000)
ret, frame1 = cap.read()
if ret: cv2.imwrite("frame_fixed_1s.jpg", frame1)

cap.set(cv2.CAP_PROP_POS_MSEC, 2500)
ret, frame2 = cap.read()
if ret: cv2.imwrite("frame_fixed_2.5s.jpg", frame2)
cap.release()

print("Re-render test complete!")
