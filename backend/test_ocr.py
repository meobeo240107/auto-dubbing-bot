import cv2
import easyocr
import json

def dump_ocr():
    reader = easyocr.Reader(['ch_sim', 'en'], gpu=True)
    cap = cv2.VideoCapture("workspace/downloads/test_bug_vid1.mp4")
    
    fps = cap.get(cv2.CAP_PROP_FPS)
    frames_to_dump = 3
    
    with open("ocr_dump.txt", "w", encoding="utf-8") as f:
        for _ in range(frames_to_dump):
            ret, frame = cap.read()
            if not ret: break
            
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
            gray = clahe.apply(gray)
            
            results = reader.readtext(gray, detail=1, paragraph=False, mag_ratio=1.5, width_ths=0.7)
            for bbox, text, prob in results:
                y1 = min(pt[1] for pt in bbox)
                y2 = max(pt[1] for pt in bbox)
                f.write(f"TEXT: {text} | Y: {y1/frame.shape[0]:.3f} - {y2/frame.shape[0]:.3f} | PROB: {prob:.3f}\n")
            f.write("---\n")
            
            # Skip 1 second
            cap.set(cv2.CAP_PROP_POS_FRAMES, cap.get(cv2.CAP_PROP_POS_FRAMES) + int(fps))
            
    cap.release()

if __name__ == "__main__":
    dump_ocr()
