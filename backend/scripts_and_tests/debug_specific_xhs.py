import requests
import json
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')

url = 'http://xhslink.com/o/2stbyFrGqXe'
headers = {
    'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8'
}

res = requests.get(url, headers=headers, allow_redirects=True, timeout=15)
print("Final URL:", res.url)
print("Status:", res.status_code)

state_match = re.search(r'window\.__INITIAL_STATE__\s*=\s*(\{.*?\})</script>', res.text, re.DOTALL)
if state_match:
    raw_json = state_match.group(1).replace("undefined", "null")
    state = json.loads(raw_json)
    note_data = state.get("noteData", {}).get("data", {}).get("noteData", {})
    print("Title:", note_data.get("title"))
    print("Desc:", note_data.get("desc"))
    video = note_data.get("video")
    print("Video object keys:", list(video.keys()) if isinstance(video, dict) else type(video))
    if isinstance(video, dict):
        print(json.dumps(video, ensure_ascii=False, indent=2))
        
        origin_key = video.get("consumer", {}).get("originVideoKey")
        print("\nOrigin key:", origin_key)
        
        if origin_key:
            origin_domains = [
                'http://sns-video-bd.xhscdn.com',
                'http://sns-video-qc.xhscdn.com',
                'http://sns-video-hw.xhscdn.com',
                'http://sns-video-al.xhscdn.com',
                'https://sns-video-bd.xhscdn.com'
            ]
            for dom in origin_domains:
                u = f"{dom}/{origin_key}"
                try:
                    h = requests.head(u, headers=headers, timeout=5)
                    print(f"Origin probe {u} -> {h.status_code}, Length: {h.headers.get('Content-Length')}")
                except Exception as e:
                    print(f"Origin probe {u} -> Error: {e}")
else:
    print("No INITIAL_STATE found!")
