import srt
import datetime

seg = srt.Subtitle(index=1, start=datetime.timedelta(seconds=0), end=datetime.timedelta(seconds=1), content="test")
seg.y_pct = 0.5
print("Before compose")
try:
    srt.compose([seg], reindex=True)
    print("Compose success")
except Exception as e:
    print(f"Error: {repr(e)}")
