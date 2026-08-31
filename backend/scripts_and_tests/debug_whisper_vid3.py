import sys
import whisper
model = whisper.load_model('base')
result = model.transcribe('workspace/downloads/test_bug_vid3.mp4')
for seg in result['segments']:
    print(f"[{seg['start']:.2f} - {seg['end']:.2f}] {seg['text']}")
