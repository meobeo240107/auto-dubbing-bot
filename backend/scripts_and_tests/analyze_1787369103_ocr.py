import cv2
import easyocr
import sys

sys.stdout.reconfigure(encoding='utf-8')

video_path = r"C:\Users\admin\.gemini\antigravity\scratch\video-dubbing-app\workspace\downloads\1787369103_2849592d_难道没有人发现它是一个防偷卡神器吗小卡打包话题_出卡打包话题_打包胶带话题.mp4"
reader = easyocr.Reader(['ch_sim'])

cap = cv2.VideoCapture(video_path)
fps = cap.get(cv2.CAP_PROP_FPS) or 30
w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
print(f"Video {w}x{h}, FPS={fps}")

for t in [1.0, 3.0, 5.5, 6.0, 8.0, 12.0, 18.0, 24.0]:
    cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
    ret, frame = cap.read()
    if not ret: continue
    
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    gray = clahe.apply(gray)
    
    results = reader.readtext(gray, detail=1, paragraph=False)
    print(f"\n--- Time: {t}s ---")
    for (bbox, text, prob) in results:
        if prob < 0.20 or len(text.strip()) < 2: continue
        ys = [pt[1] for pt in bbox]
        xs = [pt[0] for pt in bbox]
        y1, y2 = min(ys) / h, max(ys) / h
        x1, x2 = min(xs) / w, max(xs) / w
        print(f"Text: '{text}' (prob={prob:.2f}) -> Y: {y1:.3f} - {y2:.3f}, X: {x1:.2f}-{x2:.2f}")

cap.release()
