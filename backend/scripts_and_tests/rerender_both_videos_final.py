import os
import srt
import sys
import shutil

sys.path.insert(0, '.')
from ass_utils import generate_ass_file
from video_utils import process_video
from ocr_utils import perform_video_ocr

def render_final(work_dir, out_filename):
    print(f"\nProcessing {work_dir}...")
    orig_srt_path = os.path.join(work_dir, "original.srt")
    trans_srt_path = os.path.join(work_dir, "translated.srt")
    mixed_audio = os.path.join(work_dir, "mixed.wav")
    
    # Find downloaded video
    base_name = os.path.basename(work_dir)
    raw_video = os.path.join(r"C:\Users\admin\.gemini\antigravity\scratch\video-dubbing-app\workspace\downloads", f"{base_name}.mp4")
    if not os.path.exists(raw_video):
        for f in os.listdir(work_dir):
            if f.endswith(".mp4") and not f.startswith("final_"):
                raw_video = os.path.join(work_dir, f)
                break
                
    with open(orig_srt_path, "r", encoding="utf-8") as f:
        orig_segs = list(srt.parse(f.read()))
    with open(trans_srt_path, "r", encoding="utf-8") as f:
        trans_segs = list(srt.parse(f.read()))
        
    _, vid_w, vid_h, main_y_pct = perform_video_ocr(raw_video, srt_segments=orig_segs)
    
    for i, t_seg in enumerate(trans_segs):
        t_seg.y_pct = orig_segs[i].y_pct
        t_seg.max_y_pct = orig_segs[i].max_y_pct
        t_seg.best_block = getattr(orig_segs[i], 'best_block', None)
        
    final_ass = os.path.join(work_dir, "final.ass")
    generate_ass_file(trans_segs, [], final_ass, play_res_x=720, play_res_y=1280, main_y_pct=main_y_pct)
    
    final_video = os.path.join(work_dir, f"final_{base_name}.mp4")
    ok = process_video(raw_video, final_ass, mixed_audio, final_video, main_y_pct=main_y_pct, delogo=True)
    
    if ok and os.path.exists(final_video):
        dest_path = os.path.join(r"D:\banve", out_filename)
        shutil.copy2(final_video, dest_path)
        print(f"✅ Successfully updated {dest_path}")

render_final(
    r"C:\Users\admin\.gemini\antigravity\scratch\video-dubbing-app\workspace\1787371809_0d012508_一本很权威的贴纸砖",
    "Dubbed_1787371809_0d012508_一本很权威的贴纸砖.mp4"
)

render_final(
    r"C:\Users\admin\.gemini\antigravity\scratch\video-dubbing-app\workspace\1787372262_d8fd536a_这样展示贴纸美得欣赏了半小时才发",
    "Dubbed_1787372262_d8fd536a_这样展示贴纸美得欣赏了半小时才发.mp4"
)

print("\nAll videos successfully re-rendered!")
