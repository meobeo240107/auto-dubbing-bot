import json

with open("xhs_state.json", "r", encoding="utf-8") as f:
    data = json.load(f)

note_data = data.get("noteData", {})
print("noteData keys:", list(note_data.keys()))

# Look for note detail
first_id = list(note_data.keys())[0] if note_data else None
print("First key:", first_id)
if first_id:
    detail = note_data[first_id]
    print("Detail keys:", list(detail.keys()) if isinstance(detail, dict) else type(detail))
    if isinstance(detail, dict):
        print("title:", detail.get("title"))
        print("desc:", detail.get("desc"))
        video = detail.get("video")
        print("video object:", video)
        if isinstance(video, dict):
            media = video.get("media", {})
            print("media keys:", list(media.keys()))
            stream = media.get("stream", {})
            print("stream keys:", list(stream.keys()))
            for k, v in stream.items():
                print(f"stream[{k}]:", v)
