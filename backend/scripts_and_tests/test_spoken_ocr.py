import cv2
import easyocr
import srt
import sys
import difflib
import numpy as np

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, '.')
from ass_utils import generate_ass_file
from video_utils import process_video

reader = easyocr.Reader(['ch_sim'])

def test_fixed_pipeline(name, raw_vid, srt_orig_path, srt_trans_path, mixed_audio_path, out_vid_path):
    print(f"\n==================== Testing {name} ====================")
    with open(srt_orig_path, "r", encoding="utf-8") as f:
        orig_segs = list(srt.parse(f.read()))
    with open(srt_trans_path, "r", encoding="utf-8") as f:
        trans_segs = list(srt.parse(f.read()))
        
    cap = cv2.VideoCapture(raw_vid)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    duration = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) / fps
    
    # 1. Scan frames at segment centers
    all_blocks = []
    crop_y_start = int(h * 0.12)
    crop_y_end = int(h * 0.92)
    
    for seg in orig_segs:
        t_center = (seg.start.total_seconds() + seg.end.total_seconds()) / 2.0
        cap.set(cv2.CAP_PROP_POS_MSEC, t_center * 1000)
        ret, frame = cap.read()
        if not ret: continue
        
        cropped = frame[crop_y_start:crop_y_end, :]
        gray = cv2.cvtColor(cropped, cv2.COLOR_BGR2GRAY)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        gray = clahe.apply(gray)
        
        results = reader.readtext(gray, detail=1, paragraph=False, mag_ratio=1.2, width_ths=0.7)
        for (bbox, text, prob) in results:
            clean_t = text.strip()
            if prob < 0.20 or len(clean_t) == 0: continue
            ys = [pt[1] + crop_y_start for pt in bbox]
            xs = [pt[0] for pt in bbox]
            y1, y2 = min(ys) / h, max(ys) / h
            x1, x2 = min(xs) / w, max(xs) / w
            all_blocks.append({
                't': t_center, 'text': clean_t,
                'y_pct': y1, 'max_y_pct': y2,
                'x_pct': x1, 'max_x_pct': x2, 'prob': prob
            })
            
    cap.release()
    
    # 2. Match each segment to OCR text using text similarity
    matched_y_tops = []
    matched_y_bottoms = []
    
    for i, orig_seg in enumerate(orig_segs):
        seg_s = orig_seg.start.total_seconds()
        seg_e = orig_seg.end.total_seconds()
        seg_text = orig_seg.content.strip()
        
        best_sim = 0
        best_b = None
        for b in all_blocks:
            if abs(b['t'] - (seg_s + seg_e)/2.0) <= 2.0:
                sim = difflib.SequenceMatcher(None, b['text'], seg_text).ratio()
                if sim > best_sim:
                    best_sim = sim
                    best_b = b
                    
        trans_segs[i].orig_sim = best_sim
        trans_segs[i].best_b = best_b
        if best_b and best_sim >= 0.25:
            matched_y_tops.append(best_b['y_pct'])
            matched_y_bottoms.append(best_b['max_y_pct'])
            print(f"Seg {i} (MATCH {best_sim:.2f}): '{seg_text}' -> OCR '{best_b['text']}' Y: {best_b['y_pct']:.3f} - {best_b['max_y_pct']:.3f}")
            
    # Compute median from SPOKEN matched subtitles only
    if matched_y_tops:
        global_top = float(np.median(matched_y_tops))
        global_bottom = float(np.median(matched_y_bottoms))
    else:
        global_top = 0.75
        global_bottom = 0.82
        
    print(f"==> Global Spoken Subtitle Band: Top={global_top:.3f}, Bottom={global_bottom:.3f}")
    
    for i, seg in enumerate(trans_segs):
        if getattr(seg, 'best_b', None) and getattr(seg, 'orig_sim', 0) >= 0.35:
            seg.y_pct = seg.best_b['y_pct']
            seg.max_y_pct = seg.best_b['max_y_pct']
        else:
            seg.y_pct = global_top
            seg.max_y_pct = global_bottom
        seg.best_block = None
        
    # 3. Generate ASS and Render with 4-Corner Delogo
    ass_path = out_vid_path.replace(".mp4", "_test.ass")
    generate_ass_file(trans_segs, [], ass_path, play_res_x=720, play_res_y=1280, main_y_pct=global_top)
    
    ok = process_video(raw_vid, ass_path, mixed_audio_path, out_vid_path, main_y_pct=global_top, delogo=True)
    print(f"Render {name} status: {ok}")

# Test Vid1
test_fixed_pipeline(
    "Vid1",
    r"C:\Users\admin\.gemini\antigravity\scratch\video-dubbing-app\workspace\downloads\1787371809_0d012508_一本很权威的贴纸砖.mp4",
    r"C:\Users\admin\.gemini\antigravity\scratch\video-dubbing-app\workspace\1787371809_0d012508_一本很权威的贴纸砖\original.srt",
    r"C:\Users\admin\.gemini\antigravity\scratch\video-dubbing-app\workspace\1787371809_0d012508_一本很权威的贴纸砖\translated.srt",
    r"C:\Users\admin\.gemini\antigravity\scratch\video-dubbing-app\workspace\1787371809_0d012508_一本很权威的贴纸砖\mixed.wav",
    r"C:\Users\admin\.gemini\antigravity\scratch\video-dubbing-app\backend\test_vid1_fixed.mp4"
)

# Test Vid2
test_fixed_pipeline(
    "Vid2",
    r"C:\Users\admin\.gemini\antigravity\scratch\video-dubbing-app\workspace\downloads\1787372262_d8fd536a_这样展示贴纸美得欣赏了半小时才发.mp4",
    r"C:\Users\admin\.gemini\antigravity\scratch\video-dubbing-app\workspace\1787372262_d8fd536a_这样展示贴纸美得欣赏了半小时才发\original.srt",
    r"C:\Users\admin\.gemini\antigravity\scratch\video-dubbing-app\workspace\1787372262_d8fd536a_这样展示贴纸美得欣赏了半小时才发\translated.srt",
    r"C:\Users\admin\.gemini\antigravity\scratch\video-dubbing-app\workspace\1787372262_d8fd536a_这样展示贴纸美得欣赏了半小时才发\mixed.wav",
    r"C:\Users\admin\.gemini\antigravity\scratch\video-dubbing-app\backend\test_vid2_fixed.mp4"
)

# Extract frames for verification
cap = cv2.VideoCapture(r"C:\Users\admin\.gemini\antigravity\scratch\video-dubbing-app\backend\test_vid1_fixed.mp4")
cap.set(cv2.CAP_PROP_POS_MSEC, 5000)
ret, f = cap.read()
if ret: cv2.imwrite("test_vid1_fixed_5s.jpg", f)
cap.release()

cap = cv2.VideoCapture(r"C:\Users\admin\.gemini\antigravity\scratch\video-dubbing-app\backend\test_vid2_fixed.mp4")
cap.set(cv2.CAP_PROP_POS_MSEC, 8000)
ret, f = cap.read()
if ret: cv2.imwrite("test_vid2_fixed_8s.jpg", f)
cap.release()

