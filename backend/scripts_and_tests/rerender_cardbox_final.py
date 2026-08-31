import os
import srt
import sys
import shutil
sys.path.insert(0, '.')
from ass_utils import generate_ass_file
from video_utils import process_video

# 1. Load translated segments
srt_path = r"C:\Users\admin\.gemini\antigravity\scratch\video-dubbing-app\workspace\1787311966_16018c93_6小卡分格收纳盒\translated.srt"
with open(srt_path, "r", encoding="utf-8") as f:
    translated_segments = list(srt.parse(f.read()))

# 2. Set the detected top/bottom Y coordinates
for i, seg in enumerate(translated_segments):
    if i == 0:
        seg.y_pct = 0.302
        seg.max_y_pct = 0.340
    else:
        seg.y_pct = 0.263
        seg.max_y_pct = 0.298
    seg.best_block = None

# 3. Generate clean ASS
clean_ass = r"C:\Users\admin\.gemini\antigravity\scratch\video-dubbing-app\workspace\1787311966_16018c93_6小卡分格收纳盒\final.ass"
generate_ass_file(translated_segments, [], clean_ass, play_res_x=720, play_res_y=1280, main_y_pct=0.302)

# 4. Render
video_input = r"C:\Users\admin\.gemini\antigravity\scratch\video-dubbing-app\workspace\downloads\1787311966_16018c93_6小卡分格收纳盒.mp4"
mixed_audio = r"C:\Users\admin\.gemini\antigravity\scratch\video-dubbing-app\workspace\1787311966_16018c93_6小卡分格收纳盒\mixed.wav"
final_video = r"C:\Users\admin\.gemini\antigravity\scratch\video-dubbing-app\workspace\1787311966_16018c93_6小卡分格收纳盒\final_1787311966_16018c93_6小卡分格收纳盒.mp4"

ok = process_video(video_input, clean_ass, mixed_audio, final_video, main_y_pct=0.302, delogo=True)
print("Render status:", ok)

if ok and os.path.exists(final_video):
    dest_path = r"D:\banve\Dubbed_1787311966_16018c93_6小卡分格收纳盒.mp4"
    shutil.copy2(final_video, dest_path)
    print(f"Copied fixed video to {dest_path}")
