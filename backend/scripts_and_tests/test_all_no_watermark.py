import re
import json
import requests
import sys

sys.stdout.reconfigure(encoding='utf-8')

test_links = [
    'http://xhslink.com/o/12IgoDtwFtm',
    'http://xhslink.com/o/ATdSTNcDts',
    'http://xhslink.com/o/8ea48HPIQU3'
]

headers = {
    'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8'
}

origin_domains = [
    'http://sns-video-bd.xhscdn.com',
    'http://sns-video-qc.xhscdn.com',
    'http://sns-video-hw.xhscdn.com',
    'http://sns-video-al.xhscdn.com',
    'https://sns-video-bd.xhscdn.com'
]

for link in test_links:
    print(f"\nTesting {link}...")
    res = requests.get(link, headers=headers, allow_redirects=True, timeout=15)
    state_match = re.search(r'window\.__INITIAL_STATE__\s*=\s*(\{.*?\})</script>', res.text, re.DOTALL)
    if state_match:
        raw_json = state_match.group(1).replace("undefined", "null")
        state = json.loads(raw_json)
        note_data = state.get("noteData", {}).get("data", {}).get("noteData", {})
        title = note_data.get("title") or note_data.get("desc", "")
        print(f"Title: {title}")
        video = note_data.get("video", {})
        origin_key = video.get("consumer", {}).get("originVideoKey") if isinstance(video, dict) else None
        print(f"originVideoKey: {origin_key}")
        
        found_origin = False
        if origin_key:
            for dom in origin_domains:
                orig_url = f"{dom}/{origin_key}"
                try:
                    head = requests.head(orig_url, headers=headers, timeout=5)
                    if head.status_code == 200:
                        print(f"  -> SUCCESS NO-WATERMARK URL: {orig_url} (Size: {head.headers.get('Content-Length')} bytes)")
                        found_origin = True
                        break
                except:
                    pass
        if not found_origin:
            print("  -> Origin key not reachable, fallback to stream")
