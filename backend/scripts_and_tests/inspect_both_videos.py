import cv2
import easyocr
import sys
import os

sys.stdout.reconfigure(encoding='utf-8')

reader = easyocr.Reader(['ch_sim'])

vids = [
    ("Vid1", r"C:\Users\admin\.gemini\antigravity\scratch\video-dubbing-app\workspace\downloads\1787371809_0d012508_一本很权威的贴纸砖.mp4",
             r"D:\banve\Dubbed_1787371809_0d012508_一本很权威的贴纸砖.mp4"),
    ("Vid2", r"C:\Users\admin\.gemini\antigravity\scratch\video-dubbing-app\workspace\downloads\1787372262_d8fd536a_这样展示贴纸美得欣赏了半小时才发.mp4",
             r"D:\banve\Dubbed_1787372262_d8fd536a_这样展示贴纸美得欣赏了半小时才发.mp4")
]

for name, raw_path, dubbed_path in vids:
    print(f"\n==================== {name} ====================")
    print(f"Raw: {raw_path}")
    print(f"Dubbed: {dubbed_path}")
    
    cap_raw = cv2.VideoCapture(raw_path)
    w = int(cap_raw.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap_raw.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap_raw.get(cv2.CAP_PROP_FPS) or 30
    total_frames = int(cap_raw.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = total_frames / fps
    print(f"Resolution: {w}x{h}, Duration: {duration:.1f}s")
    
    # Save frames from raw to check watermark and subtitle position
    for t in [1.0, 3.0, 5.0, 10.0]:
        cap_raw.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
        ret, frame = cap_raw.read()
        if ret:
            cv2.imwrite(f"{name}_raw_{t}s.jpg", frame)
            
            # Run OCR on frame
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
            gray = clahe.apply(gray)
            results = reader.readtext(gray, detail=1, paragraph=False)
            print(f"\n--- {name} at {t}s ---")
            for (bbox, text, prob) in results:
                if prob < 0.20 or len(text.strip()) == 0: continue
                ys = [pt[1] for pt in bbox]
                xs = [pt[0] for pt in bbox]
                y1, y2 = min(ys) / h, max(ys) / h
                x1, x2 = min(xs) / w, max(xs) / w
                print(f"Text: '{text}' (prob={prob:.2f}) -> Y: {y1:.3f} - {y2:.3f}, X: {x1:.2f}-{x2:.2f}")

    cap_raw.release()
    
    # Save frames from dubbed to inspect current result
    cap_dub = cv2.VideoCapture(dubbed_path)
    for t in [1.0, 3.0, 5.0, 10.0]:
        cap_dub.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
        ret, frame = cap_dub.read()
        if ret:
            cv2.imwrite(f"{name}_dubbed_{t}s.jpg", frame)
    cap_dub.release()

print("\nAnalysis script finished!")
