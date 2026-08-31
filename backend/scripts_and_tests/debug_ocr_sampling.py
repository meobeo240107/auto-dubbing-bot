import cv2
import easyocr
import sys
import os
import re
import difflib

sys.stdout.reconfigure(encoding='utf-8')

video_path = r"C:\Users\admin\.gemini\antigravity\scratch\video-dubbing-app\workspace\downloads\1787369103_2849592d_难道没有人发现它是一个防偷卡神器吗小卡打包话题_出卡打包话题_打包胶带话题.mp4"
reader = easyocr.Reader(['ch_sim'])

cap = cv2.VideoCapture(video_path)
fps = cap.get(cv2.CAP_PROP_FPS) or 30
total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
duration = total_frames / fps
height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))

target_timestamps = []
for pct in [0.2, 0.35, 0.5, 0.65, 0.8, 0.9]:
    target_timestamps.append(duration * pct)

crop_y_start = int(height * 0.15)
crop_y_end = int(height * 0.92)

all_detected = []
for t in target_timestamps:
    cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
    ret, frame = cap.read()
    if not ret: continue
    
    cropped_frame = frame[crop_y_start:crop_y_end, :]
    gray = cv2.cvtColor(cropped_frame, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    gray = clahe.apply(gray)
    
    results = reader.readtext(gray, detail=1, paragraph=False, mag_ratio=1.2, width_ths=0.7)
    print(f"\n--- Timestamp {t:.2f}s ---")
    for (bbox, text, prob) in results:
        clean_t = text.strip()
        ys = [pt[1] + crop_y_start for pt in bbox] # BÙ LẠI VỊ TRÍ CẮT DỌC
        y1, y2 = min(ys) / height, max(ys) / height
        print(f"Detected: '{clean_t}' (prob={prob:.2f}) -> Y: {y1:.3f} - {y2:.3f}")
        if prob >= 0.25 and len(clean_t) >= 2:
            all_detected.append((clean_t, y1, y2, prob))

cap.release()

print("\n=== ALL VALID BLOCKS ===")
for text, y1, y2, prob in all_detected:
    print(f"'{text}' -> Y: {y1:.3f} - {y2:.3f}")
