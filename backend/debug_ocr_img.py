import cv2
import easyocr
import sys

def debug_ocr():
    img_path = 'frame1.jpg'
    img = cv2.imread(img_path)
    if img is None:
        print("Could not read frame1.jpg")
        return
        
    print(f"Image shape: {img.shape}")
    
    reader = easyocr.Reader(['ch_sim', 'en'], gpu=True)
    
    # Test 1: Raw image
    print("--- RAW IMAGE ---")
    results = reader.readtext(img)
    for bbox, text, prob in results:
        print(f"[{prob:.2f}] {text.encode('utf-8', 'replace').decode('utf-8')}")
        
    # Test 2: Invert image (sometimes white text on light bg is hard)
    print("--- INVERTED ---")
    inverted = cv2.bitwise_not(img)
    results = reader.readtext(inverted)
    for bbox, text, prob in results:
        print(f"[{prob:.2f}] {text.encode('utf-8', 'replace').decode('utf-8')}")

    # Test 3: Grayscale + Threshold
    print("--- THRESHOLD ---")
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)
    results = reader.readtext(thresh)
    for bbox, text, prob in results:
        print(f"[{prob:.2f}] {text.encode('utf-8', 'replace').decode('utf-8')}")

if __name__ == "__main__":
    debug_ocr()
