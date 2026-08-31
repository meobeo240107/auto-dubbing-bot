import requests
import sys

sys.stdout.reconfigure(encoding='utf-8')

key = '1040g2so323l51a6m7u704a3t1aardgl6tcp11lg'

prefixes = ['', 'pre_post/', 'post/', 'video/', 'stream/']
domains = [
    'http://sns-video-bd.xhscdn.com',
    'https://sns-video-bd.xhscdn.com',
    'http://sns-video-qc.xhscdn.com',
    'http://sns-video-hw.xhscdn.com',
    'http://sns-video-al.xhscdn.com',
    'http://sns-video-tx.xhscdn.com',
    'http://sns-video-zl.xhscdn.com'
]

headers = {
    'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15'
}

for p in prefixes:
    for d in domains:
        u = f"{d}/{p}{key}"
        try:
            r = requests.head(u, headers=headers, timeout=3)
            if r.status_code == 200:
                print(f"FOUND 200 SUCCESS: {u} -> Length: {r.headers.get('Content-Length')}")
        except Exception as e:
            pass

print("Testing all prefixes complete.")
