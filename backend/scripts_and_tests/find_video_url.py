import json

with open("xhs_state.json", "r", encoding="utf-8") as f:
    data = json.load(f)

def find_urls(obj, path=""):
    if isinstance(obj, dict):
        for k, v in obj.items():
            find_urls(v, f"{path}.{k}" if path else k)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            find_urls(v, f"{path}[{i}]")
    elif isinstance(obj, str):
        if obj.startswith("http") and any(ext in obj for ext in [".mp4", "sns-video", "xhscdn", "spectrum", "video"]):
            print(f"Found URL at {path}: {obj[:120]}")

find_urls(data)

note_data = data.get("noteData", {})
if "data" in note_data:
    print("\nnoteData.data type:", type(note_data["data"]))
    if isinstance(note_data["data"], dict):
        print("noteData.data keys:", list(note_data["data"].keys()))
        note_detail = note_data["data"].get("noteData", {}) or note_data["data"]
        print("note detail keys:", list(note_detail.keys()) if isinstance(note_detail, dict) else type(note_detail))
