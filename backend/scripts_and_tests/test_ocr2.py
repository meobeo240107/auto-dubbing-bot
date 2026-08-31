import cv2
import easyocr

def dump_ocr():
    reader = easyocr.Reader(['ch_sim', 'en'], gpu=True)
    # The user says "video này" and uploaded an image for 6BlzlHbKmpi
    video_path = "workspace/downloads/test_bug_vid2.mp4"
    cap = cv2.VideoCapture(video_path)
    
    cap.set(cv2.CAP_PROP_POS_FRAMES, 50) # Get a frame where the text is visible
    ret, frame = cap.read()
    
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    gray = clahe.apply(gray)
    
    results = reader.readtext(gray, detail=1, paragraph=False, mag_ratio=1.5, width_ths=0.7)
    
    for bbox, text, prob in results:
        y1 = min(pt[1] for pt in bbox)
        y2 = max(pt[1] for pt in bbox)
        print(f"[{prob:.2f}] Y: {y1/frame.shape[0]:.3f}-{y2/frame.shape[0]:.3f} | {text.encode('utf-8', 'replace').decode('utf-8')}")
        
    cap.release()

if __name__ == "__main__":
    dump_ocr()
