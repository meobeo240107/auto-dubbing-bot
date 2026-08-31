import requests
import json
import re
import cv2
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

url = 'https://www.xiaohongshu.com/discovery/item/6a78495e0000000033032c03?app_platform=ios&app_version=9.41.2&share_from_user_hidden=true&xsec_source=app_share&type=video&xsec_token=CBRQD7yHIw-4I56N8R6JO5f9_YD_H3ttAKobUR3s9xqIE=&author_share=1&xhsshare=CopyLink&shareRedId=OD5DNDNJNjo2NzUyOTgwNjc8OThKPkdL&apptime=1787201155&share_id=f18a69c1e30c460b96f3233b85a14a0d'

headers = {
    'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8'
}

res = requests.get(url, headers=headers, allow_redirects=True, timeout=15)
print("Final URL:", res.url)

state_match = re.search(r'window\.__INITIAL_STATE__\s*=\s*(\{.*?\})</script>', res.text, re.DOTALL)
if state_match:
    raw_json = state_match.group(1).replace("undefined", "null")
    state = json.loads(raw_json)
    note_data = state.get("noteData", {}).get("data", {}).get("noteData", {})
    print("Title:", note_data.get("title"))
    print("Desc:", note_data.get("desc"))
    video = note_data.get("video")
    if isinstance(video, dict):
        origin_key = video.get("consumer", {}).get("originVideoKey")
        print("\nOrigin key:", origin_key)
        
        origin_domains = [
            'http://sns-video-bd.xhscdn.com',
            'https://sns-video-bd.xhscdn.com',
            'http://sns-video-qc.xhscdn.com',
            'http://sns-video-hw.xhscdn.com',
            'http://sns-video-al.xhscdn.com'
        ]
        for dom in origin_domains:
            if origin_key:
                u = f"{dom}/{origin_key}"
                try:
                    h = requests.head(u, headers=headers, timeout=5)
                    print(f"Origin probe {u} -> Status {h.status_code}, Length: {h.headers.get('Content-Length')}")
                except Exception as e:
                    print(f"Origin probe {u} -> Error: {e}")
                    
        media = video.get("media", {})
        stream = media.get("stream", {})
        for st_type in ['h264', 'h265']:
            st_list = stream.get(st_type, [])
            for item in st_list:
                print(f"Stream {st_type}: {item.get('masterUrl')[:80]}")
else:
    print("No INITIAL_STATE found!")
