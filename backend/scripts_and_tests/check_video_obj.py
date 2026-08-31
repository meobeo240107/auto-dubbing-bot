import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

with open("xhs_state.json", "r", encoding="utf-8") as f:
    data = json.load(f)

note_data = data.get("noteData", {}).get("data", {}).get("noteData", {})
print("title:", note_data.get("title"))
video = note_data.get("video")
if video:
    media = video.get("media", {})
    stream = media.get("stream", {})
    print("stream keys:", list(stream.keys()))
    for stream_type, stream_items in stream.items():
        if isinstance(stream_items, list):
            for item in stream_items:
                master_url = item.get("masterUrl") or item.get("url")
                print(f"Stream {stream_type} masterUrl: {master_url}")
                backup_urls = item.get("backupUrls", [])
                print(f"Stream {stream_type} backupUrls: {backup_urls}")
else:
    print("video is None! Is this an image post or video post? Type:", note_data.get("type"))
