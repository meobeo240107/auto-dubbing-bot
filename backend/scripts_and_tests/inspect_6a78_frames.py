import requests
import cv2
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

stream_url = 'http://sns-video-zl.xhscdn.com/stream/79/110/259/01ea78495e58c7a0010370039fe5e08171_259.mp4?sign=2ebb88c69517b5500d5d757756801577&t=6a8b973f'
headers = {
    'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15'
}

r = requests.get(stream_url, headers=headers, stream=True)
with open("test_6a78_stream.mp4", "wb") as f:
    for chunk in r.iter_content(512*1024):
        if chunk: f.write(chunk)

print(f"Downloaded stream: {os.path.getsize('test_6a78_stream.mp4')} bytes")

cap = cv2.VideoCapture("test_6a78_stream.mp4")
fps = cap.get(cv2.CAP_PROP_FPS) or 30
total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
print(f"FPS: {fps}, Total frames: {total}, Width: {cap.get(cv2.CAP_PROP_FRAME_WIDTH)}, Height: {cap.get(cv2.CAP_PROP_FRAME_HEIGHT)}")

# Save frames at 1s, 5s, 10s, 30s
for sec in [1, 5, 10, 30]:
    cap.set(cv2.CAP_PROP_POS_FRAMES, int(sec * fps))
    ret, frame = cap.read()
    if ret:
        cv2.imwrite(f"frame_6a78_{sec}s.jpg", frame)
        print(f"Saved frame_6a78_{sec}s.jpg")

cap.release()
