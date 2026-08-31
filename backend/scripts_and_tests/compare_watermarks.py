import requests
import os
import cv2
import sys

sys.stdout.reconfigure(encoding='utf-8')

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
}

origin_url = 'http://sns-video-bd.xhscdn.com/pre_post/1040g2t0323qhv950744g5n21ujghaj977vjudfo'
stream_url = 'http://sns-video-v27.xhscdn.com/stream/79/110/259/01ea7dd0f15416ba010370039ffb7a5d6d_259.mp4?sign=778547ca8684c22725be63b93bbb032d&t=6a887a12'

print("1. Downloading origin video...")
with requests.get(origin_url, headers=headers, stream=True) as r:
    r.raise_for_status()
    with open('test_2stby_origin.mp4', 'wb') as f:
        for chunk in r.iter_content(512*1024):
            if chunk: f.write(chunk)
print(f"Origin size: {os.path.getsize('test_2stby_origin.mp4')} bytes")

print("2. Downloading stream video...")
with requests.get(stream_url, headers=headers, stream=True) as r:
    r.raise_for_status()
    with open('test_2stby_stream.mp4', 'wb') as f:
        for chunk in r.iter_content(512*1024):
            if chunk: f.write(chunk)
print(f"Stream size: {os.path.getsize('test_2stby_stream.mp4')} bytes")

# Extract first and last frames from both to check for watermarks
for name in ['test_2stby_origin.mp4', 'test_2stby_stream.mp4']:
    cap = cv2.VideoCapture(name)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    print(f"\n{name} total frames: {total_frames}, res: {int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))}x{int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))}")
    
    # Save frame at 1s and at end
    cap.set(cv2.CAP_PROP_POS_FRAMES, int(cap.get(cv2.CAP_PROP_FPS) * 1.5))
    ret, frame1 = cap.read()
    if ret:
        cv2.imwrite(f"{name}_frame_1s.jpg", frame1)
        
    cap.set(cv2.CAP_PROP_POS_FRAMES, max(0, total_frames - 10))
    ret, frame_end = cap.read()
    if ret:
        cv2.imwrite(f"{name}_frame_end.jpg", frame_end)
    cap.release()

print("\nDone extracting frames!")
