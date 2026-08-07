import os
import parselmouth
import numpy as np

print("Extracting audio...")
os.system("ffmpeg -y -i target_video.mp4 -vn -acodec pcm_s16le -ar 16000 -ac 1 target_audio.wav 2>NUL")

print("Analyzing pitch...")
snd = parselmouth.Sound("target_audio.wav")
pitch = snd.to_pitch()
pitch_values = pitch.selected_array['frequency']
voiced = pitch_values[pitch_values > 0]
if len(voiced) > 0:
    print(f"MEDIAN PITCH: {np.median(voiced):.2f} Hz")
    print(f"MEAN PITCH: {np.mean(voiced):.2f} Hz")
    print(f"PITCH MIN: {np.percentile(voiced, 5):.2f} Hz")
    print(f"PITCH MAX: {np.percentile(voiced, 95):.2f} Hz")
else:
    print("No voiced frames found.")
