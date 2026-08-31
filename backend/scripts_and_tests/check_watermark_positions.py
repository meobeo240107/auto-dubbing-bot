import cv2
import sys

sys.stdout.reconfigure(encoding='utf-8')

def check_video_corners(video_path, name):
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = total_frames / fps
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    print(f"\n--- Checking {name} ({duration:.1f}s) ---")
    for t in [0.5, 2.0, 4.0, 8.0, 15.0, 20.0, 25.0, 30.0]:
        if t >= duration: break
        cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
        ret, frame = cap.read()
        if ret:
            cv2.imwrite(f"{name}_raw_t{int(t)}s.jpg", frame)
    cap.release()

check_video_corners(r"C:\Users\admin\.gemini\antigravity\scratch\video-dubbing-app\workspace\downloads\1787371809_0d012508_一本很权威的贴纸砖.mp4", "vid1")
check_video_corners(r"C:\Users\admin\.gemini\antigravity\scratch\video-dubbing-app\workspace\downloads\1787372262_d8fd536a_这样展示贴纸美得欣赏了半小时才发.mp4", "vid2")
print("Saved corner inspection frames!")
