import sys
import cv2
import easyocr

def debug_ocr_video():
    video_path = "workspace/downloads/test_bug_vid3.mp4"
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print("Could not open video")
        return
        
    reader = easyocr.Reader(['ch_sim', 'en'], gpu=True)
    
    fps = cap.get(cv2.CAP_PROP_FPS)
    print(f"FPS: {fps}")
    
    # We want to check frame around 3 seconds or when the text appears
    # Let's just sample every 1 second
    frame_idx = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break
            
        current_time = frame_idx / fps
        if current_time % 1.0 < (1/fps):
            print(f"\n--- TIME: {current_time:.2f} ---")
            
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
            gray = clahe.apply(gray)
            
            results = reader.readtext(gray, detail=1, paragraph=False, mag_ratio=1.5, width_ths=0.7)
            for bbox, text, prob in results:
                if len(text.strip()) == 0: continue
                
                xs = [pt[0] for pt in bbox]
                ys = [pt[1] for pt in bbox]
                x1, x2 = min(xs), max(xs)
                y1, y2 = min(ys), max(ys)
                
                h, w = frame.shape[:2]
                y_pct = y1 / h
                max_y_pct = y2 / h
                
                print(f"[{prob:.2f}] (y:{y_pct:.2f}-{max_y_pct:.2f}) {text.encode('utf-8', 'replace').decode('utf-8')}")
                
        frame_idx += 1
        if current_time > 10:  # just test first 10 seconds
            break
            
    cap.release()

if __name__ == "__main__":
    debug_ocr_video()
