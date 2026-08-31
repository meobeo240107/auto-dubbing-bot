import requests
import json
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')

url = 'http://xhslink.com/o/33X6Fat6Bbw'
headers = {
    'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8'
}
res = requests.get(url, headers=headers, allow_redirects=True, timeout=15)
state_match = re.search(r'window\.__INITIAL_STATE__\s*=\s*(\{.*?\})</script>', res.text, re.DOTALL)
if state_match:
    raw_json = state_match.group(1).replace("undefined", "null")
    state = json.loads(raw_json)
    note_data = state.get("noteData", {}).get("data", {}).get("noteData", {})
    video = note_data.get("video", {})
    stream = video.get("media", {}).get("stream", {})
    for k, v in stream.items():
        if v:
            print(f"Stream {k}: size={v[0].get('size')}, url={v[0].get('masterUrl')[:80]}")
