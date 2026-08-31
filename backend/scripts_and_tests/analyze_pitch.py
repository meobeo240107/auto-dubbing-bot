import parselmouth
import numpy as np
import subprocess
import os

# Extract audio using ffmpeg
video_path = r"C:\Users\admin\.gemini\antigravity\scratch\video-dubbing-app\workspace\downloads\target_voice.mp4"
audio_path = r"C:\Users\admin\.gemini\antigravity\scratch\video-dubbing-app\workspace\downloads\temp_audio.wav"
if os.path.exists(audio_path):
    os.remove(audio_path)
subprocess.run(['ffmpeg', '-i', video_path, '-vn', '-acodec', 'pcm_s16le', '-ar', '16000', '-ac', '1', audio_path, '-y'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

snd = parselmouth.Sound(audio_path)
pitch = snd.to_pitch()
pitch_values = pitch.selected_array['frequency']
pitch_values = pitch_values[pitch_values > 0] # Filter unvoiced frames

if len(pitch_values) > 0:
    median_pitch = np.median(pitch_values)
    mean_pitch = np.mean(pitch_values)
    std_pitch = np.std(pitch_values)
    q1 = np.percentile(pitch_values, 25)
    q3 = np.percentile(pitch_values, 75)
    print(f"Median Pitch: {median_pitch:.2f} Hz")
    print(f"Mean Pitch: {mean_pitch:.2f} Hz")
    print(f"Pitch Range (Q1 - Q3): {q1:.2f} Hz - {q3:.2f} Hz")
    print(f"Std Dev: {std_pitch:.2f} Hz")
    
    if median_pitch < 150:
        print("Gender Guess: Male (Low pitch)")
    elif 150 <= median_pitch < 185:
        print("Gender Guess: Female or High-pitched Male")
    else:
        print("Gender Guess: Female (High pitch)")
else:
    print("Could not detect pitch.")

# Clean up
if os.path.exists(audio_path):
    os.remove(audio_path)
