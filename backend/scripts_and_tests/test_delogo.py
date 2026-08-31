import subprocess
import cv2
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

input_vid = 'test_6a78_stream.mp4'
cap = cv2.VideoCapture(input_vid)
w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
cap.release()

print(f"Video resolution: {w}x{h}")

# Bottom right watermark: x ≈ w - 140, y ≈ h - 80, w ≈ 130, h ≈ 70
# Bottom left author ID: x ≈ 10, y ≈ h - 80, w ≈ 280, h ≈ 70

# Test delogo filter on both corners
delogo_filter = f"delogo=x={w-135}:y={h-75}:w=130:h=70,delogo=x=10:y={h-75}:w=280:h=70"

cmd = [
    'ffmpeg', '-y',
    '-ss', '0', '-t', '5',
    '-i', input_vid,
    '-vf', delogo_filter,
    '-c:v', 'libx264', '-preset', 'ultrafast',
    'test_delogo.mp4'
]

subprocess.run(cmd, check=True)

# Extract frame from delogo result
cap2 = cv2.VideoCapture('test_delogo.mp4')
cap2.set(cv2.CAP_PROP_POS_FRAMES, 30)
ret, frame = cap2.read()
if ret:
    cv2.imwrite('frame_delogo_result.jpg', frame)
    print("Saved frame_delogo_result.jpg!")
cap2.release()
