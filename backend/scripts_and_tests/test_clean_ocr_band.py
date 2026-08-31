import cv2
import easyocr
import sys
import numpy as np

sys.stdout.reconfigure(encoding='utf-8')

video_path = r"C:\Users\admin\.gemini\antigravity\scratch\video-dubbing-app\workspace\downloads\1787306557_251c4c13_不看尺寸的下场.mp4"
reader = easyocr.Reader(['ch_sim'])

cap = cv2.VideoCapture(video_path)
fps = cap.get(cv2.CAP_PROP_FPS) or 30
w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

crop_y_start = int(h * 0.45)

high_conf_y_top = []
high_conf_y_bottom = []

for t in [0.5, 1.5, 2.5, 4.0, 7.5, 10.0, 15.0, 20.0]:
    cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
    ret, frame = cap.read()
    if not ret: continue
    
    bottom_frame = frame[crop_y_start:, :]
    gray = cv2.cvtColor(bottom_frame, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    gray = clahe.apply(gray)
    
    results = reader.readtext(gray, detail=1, paragraph=False)
    for (bbox, text, prob) in results:
        # Lọc bỏ nhiễu có độ tin cậy thấp
        if prob < 0.30 or len(text.strip()) < 2:
            continue
            
        ys = [pt[1] + crop_y_start for pt in bbox]
        y1, y2 = min(ys) / h, max(ys) / h
        
        # Chỉ lấy các block nằm ở vùng phụ đề hợp lệ
        if 0.50 < y1 < 0.90:
            high_conf_y_top.append(y1)
            high_conf_y_bottom.append(y2)
            print(f"[{t}s] '{text}' (prob={prob:.2f}) -> Y: {y1:.3f} - {y2:.3f}")

cap.release()

if high_conf_y_top:
    med_top = float(np.median(high_conf_y_top))
    med_bottom = float(np.median(high_conf_y_bottom))
    print(f"\n=> GLOBAL CLEAN SUBTITLE BAND: Top={med_top:.3f} ({med_top*100:.1f}%), Bottom={med_bottom:.3f} ({med_bottom*100:.1f}%)")
    print(f"In 720x1280 ASS coordinates: Top={int(med_top*1280)}px, Bottom={int(med_bottom*1280)}px")
