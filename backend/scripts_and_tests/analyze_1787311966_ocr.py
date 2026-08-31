import cv2
import easyocr
import sys

sys.stdout.reconfigure(encoding='utf-8')

video_path = r"C:\Users\admin\.gemini\antigravity\scratch\video-dubbing-app\workspace\downloads\1787311966_16018c93_6小卡分格收纳盒.mp4"
reader = easyocr.Reader(['ch_sim'])

cap = cv2.VideoCapture(video_path)
fps = cap.get(cv2.CAP_PROP_FPS) or 30
w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
print(f"Video {w}x{h}, FPS={fps}")

for t in [0.5, 1.0, 2.0, 4.0, 6.0, 8.0, 10.0, 13.0]:
    cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
    ret, frame = cap.read()
    if not ret: continue
    
    # Quét toàn bộ 75% chiều cao (từ 15% đến 90%)
    crop_y_start = int(h * 0.15)
    crop_y_end = int(h * 0.90)
    cropped_frame = frame[crop_y_start:crop_y_end, :]
    
    gray = cv2.cvtColor(cropped_frame, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    gray = clahe.apply(gray)
    
    results = reader.readtext(gray, detail=1, paragraph=False)
    print(f"\n--- Time: {t}s ---")
    for (bbox, text, prob) in results:
        ys = [pt[1] + crop_y_start for pt in bbox]
        xs = [pt[0] for pt in bbox]
        y1, y2 = min(ys) / h, max(ys) / h
        x1, x2 = min(xs) / w, max(xs) / w
        print(f"Text: '{text}' (prob={prob:.2f}) -> Y: {y1:.3f} - {y2:.3f}, X: {x1:.2f}-{x2:.2f}")

cap.release()
