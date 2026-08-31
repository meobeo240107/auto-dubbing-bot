import requests
import cv2
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

urls = {
    'master_v27': 'http://sns-video-v27.xhscdn.com/stream/79/110/259/01ea7dd0f15416ba010370039ffb7a5d6d_259.mp4?sign=778547ca8684c22725be63b93bbb032d&t=6a887a12',
    'bak_v8': 'http://sns-bak-v8.xhscdn.com/stream/79/110/259/01ea7dd0f15416ba010370039ffb7a5d6d_259.mp4',
    'bak_v10': 'http://sns-bak-v10.xhscdn.com/stream/79/110/259/01ea7dd0f15416ba010370039ffb7a5d6d_259.mp4'
}

for name, u in urls.items():
    try:
        print(f"Downloading {name} from {u[:60]}...")
        r = requests.get(u, timeout=10)
        fname = f"test_{name}.mp4"
        with open(fname, "wb") as f:
            f.write(r.content)
        print(f"  -> Saved {fname}, size: {os.path.getsize(fname)} bytes")
        
        cap = cv2.VideoCapture(fname)
        cap.set(cv2.CAP_PROP_POS_FRAMES, 30)
        ret, frame = cap.read()
        if ret:
            cv2.imwrite(f"frame_{name}.jpg", frame)
            print(f"  -> Saved frame_{name}.jpg ({frame.shape})")
        cap.release()
    except Exception as e:
        print(f"Error {name}: {e}")
