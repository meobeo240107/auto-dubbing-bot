import requests
import json
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')

key = '1040g2so323l51a6m7u704a3t1aardgl6tcp11lg'

cdns = [
    'sns-video-bd.xhscdn.com',
    'sns-video-qc.xhscdn.com',
    'sns-video-hw.xhscdn.com',
    'sns-video-al.xhscdn.com',
    'sns-video-tx.xhscdn.com',
    'sns-video-zl.xhscdn.com',
    'sns-video-ali.xhscdn.com',
    'sns-video-hw1.xhscdn.com',
    'sns-video-qn.xhscdn.com',
    'sns-video-v27.xhscdn.com',
    'sns-video-v28.xhscdn.com',
    'sns-video-v29.xhscdn.com',
    'sns-video-v30.xhscdn.com',
    'v.xiaohongshu.com',
    'video.xiaohongshu.com'
]

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Referer': 'https://www.xiaohongshu.com/'
}

for c in cdns:
    for proto in ['http', 'https']:
        for path in [f"{key}", f"pre_post/{key}", f"stream/{key}", f"media/{key}"]:
            u = f"{proto}://{c}/{path}"
            try:
                r = requests.head(u, headers=headers, timeout=2)
                if r.status_code == 200:
                    print(f"FOUND CDN SUCCESS: {u} (Length: {r.headers.get('Content-Length')})")
            except:
                pass

print("\nTesting third-party API / scrapers for XHS...")
# Test tikwm / third party parser
xhs_url = 'https://www.xiaohongshu.com/discovery/item/6a78495e0000000033032c03'
try:
    api_res = requests.post("https://www.tikwm.com/api/", data={"url": xhs_url}, timeout=5)
    print("TikWM response:", api_res.json())
except Exception as e:
    print("TikWM error:", e)
