import cv2
import easyocr

def dump_ocr():
    reader = easyocr.Reader(['ch_sim', 'en'], gpu=True)
    cap = cv2.VideoCapture("workspace/downloads/test_bug_vid1.mp4")
    
    cap.set(cv2.CAP_PROP_POS_FRAMES, 30) # get a frame 1 second in
    ret, frame = cap.read()
    
    # WITH CLAHE
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    gray_clahe = clahe.apply(gray)
    
    print("=== WITH CLAHE ===")
    results1 = reader.readtext(gray_clahe, detail=1, paragraph=False)
    for bbox, text, prob in results1:
        if prob > 0.1:
            print(f"[{prob:.2f}] {text.encode('utf-8', 'replace').decode('utf-8')}")
            
    print("\n=== WITHOUT CLAHE (just gray) ===")
    results2 = reader.readtext(gray, detail=1, paragraph=False)
    for bbox, text, prob in results2:
        if prob > 0.1:
            print(f"[{prob:.2f}] {text.encode('utf-8', 'replace').decode('utf-8')}")
            
    print("\n=== RAW COLOR ===")
    results3 = reader.readtext(frame, detail=1, paragraph=False)
    for bbox, text, prob in results3:
        if prob > 0.1:
            print(f"[{prob:.2f}] {text.encode('utf-8', 'replace').decode('utf-8')}")

if __name__ == "__main__":
    dump_ocr()
