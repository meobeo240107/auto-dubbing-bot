import cv2
import easyocr
import sys

sys.stdout.reconfigure(encoding='utf-8')

video_path = r"C:\Users\admin\.gemini\antigravity\scratch\video-dubbing-app\workspace\downloads\1787306557_251c4c13_不看尺寸的下场.mp4"
reader = easyocr.Reader(['ch_sim'])

cap = cv2.VideoCapture(video_path)
fps = cap.get(cv2.CAP_PROP_FPS) or 30
w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
print(f"Video {w}x{h}, FPS={fps}")

for t in [0.5, 1.0, 1.5, 2.5, 4.0, 7.5, 10.0]:
    cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
    ret, frame = cap.read()
    if not ret: continue
    
    crop_y_start = int(h * 0.45)
    bottom_frame = frame[crop_y_start:, :]
    
    gray = cv2.cvtColor(bottom_frame, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    gray = clahe.apply(gray)
    
    results = reader.readtext(gray, detail=1, paragraph=False)
    print(f"\n--- Time: {t}s ---")
    for (bbox, text, prob) in results:
        ys = [pt[1] + crop_y_start for pt in bbox]
        xs = [pt[0] for pt in bbox]
        y1, y2 = min(ys), max(ys)
        x1, x2 = min(xs), max(xs)
        y_pct = y1 / h
        max_y_pct = y2 / h
        print(f"Text: '{text}' (prob={prob:.2f}) -> Y: {y_pct:.3f} - {max_y_pct:.3f}, X: {x1/w:.2f}-{x2/w:.2f}")

cap.release()
