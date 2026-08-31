import cv2
import subprocess
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

video_path = 'test_6a78_stream.mp4'
cap = cv2.VideoCapture(video_path)
w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
cap.release()

# Calculate dynamic corner watermark bounding boxes relative to video width & height
# Watermark in Xiaohongshu stream:
# Bottom right logo: width ~ 18% of W, height ~ 6% of H
# Bottom left author: width ~ 38% of W, height ~ 6% of H

delogo_br_w = int(w * 0.19)
delogo_br_h = int(h * 0.065)
delogo_br_x = w - delogo_br_w - int(w * 0.01)
delogo_br_y = h - delogo_br_h - int(h * 0.01)

delogo_bl_w = int(w * 0.38)
delogo_bl_h = int(h * 0.065)
delogo_bl_x = int(w * 0.01)
delogo_bl_y = h - delogo_bl_h - int(h * 0.01)

vf_delogo = f"delogo=x={delogo_br_x}:y={delogo_br_y}:w={delogo_br_w}:h={delogo_br_h},delogo=x={delogo_bl_x}:y={delogo_bl_y}:w={delogo_bl_w}:h={delogo_bl_h}"

output_video = "test_6a78_clean_rendered.mp4"

cmd = [
    'ffmpeg', '-y',
    '-ss', '0', '-t', '10',
    '-i', video_path,
    '-vf', vf_delogo,
    '-c:v', 'h264_nvenc', '-preset', 'fast',
    '-pix_fmt', 'yuv420p',
    output_video
]

subprocess.run(cmd, check=True)

cap = cv2.VideoCapture(output_video)
for s in [1, 5, 9]:
    cap.set(cv2.CAP_PROP_POS_FRAMES, int(s * 30))
    ret, frame = cap.read()
    if ret:
        cv2.imwrite(f"frame_clean_{s}s.jpg", frame)
cap.release()
print("Clean render test successful!")
