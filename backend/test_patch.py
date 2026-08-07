import os
import subprocess

# The global patch from telegram_bot.py
patched_called = False
if os.name == 'nt':
    original_init = subprocess.Popen.__init__
    def patched_init(self, *args, **kwargs):
        global patched_called
        patched_called = True
        if hasattr(subprocess, 'CREATE_NO_WINDOW'):
            kwargs['creationflags'] = kwargs.get('creationflags', 0) | subprocess.CREATE_NO_WINDOW
        original_init(self, *args, **kwargs)
    subprocess.Popen.__init__ = patched_init

# Now import pydub and see if patched_init is called
import sys
from pydub import AudioSegment
import numpy as np

import asyncio
import edge_tts
import librosa
import os

async def test_librosa():
    global patched_called
    # 1. Create MP3
    comm = edge_tts.Communicate("Hello", "vi-VN-HoaiMyNeural")
    await comm.save("test_edge.mp3")
    
    # 2. Test librosa
    patched_called = False
    try:
        y, sr = librosa.load("test_edge.mp3", sr=16000)
    except Exception as e:
        print(f"Librosa error: {e}")
    print(f"Patched called during librosa: {patched_called}")
    
    if os.path.exists("test_edge.mp3"):
        os.remove("test_edge.mp3")

asyncio.run(test_librosa())
