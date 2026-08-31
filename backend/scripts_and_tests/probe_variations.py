import requests
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')

fileid_base = '01ea78495e58c7a0010370039fe5e08171'
key = '1040g2so323l51a6m7u704a3t1aardgl6tcp11lg'

domains = [
    'http://sns-video-bd.xhscdn.com',
    'http://sns-video-zl.xhscdn.com',
    'http://sns-video-qc.xhscdn.com',
    'http://sns-video-hw.xhscdn.com',
    'http://sns-video-al.xhscdn.com',
    'http://sns-video-tx.xhscdn.com'
]

test_paths = [
    f"{fileid_base}.mp4",
    f"stream/79/110/0/{fileid_base}.mp4",
    f"stream/79/110/1000/{fileid_base}.mp4",
    f"stream/79/110/110/{fileid_base}.mp4",
    f"stream/79/110/259/{fileid_base}.mp4",
    f"stream/1/110/259/{fileid_base}.mp4",
    f"{key}.mp4",
    f"pre_post/{key}.mp4",
    f"post/{key}.mp4",
    f"origin/{key}",
    f"origin/{fileid_base}.mp4",
    f"video/{fileid_base}.mp4"
]

headers = {
    'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15'
}

for d in domains:
    for p in test_paths:
        u = f"{d}/{p}"
        try:
            r = requests.head(u, headers=headers, timeout=2)
            if r.status_code == 200:
                print(f"MATCH 200: {u} -> Length: {r.headers.get('Content-Length')}")
        except:
            pass

print("Done probing!")
