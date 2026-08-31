import requests
import time
import sys

sys.stdout.reconfigure(encoding='utf-8')

key = 'pre_post/1040g2t0323qhv950744g5n21ujghaj977vjudfo'

domains = [
    'http://sns-video-bd.xhscdn.com',
    'http://sns-video-qc.xhscdn.com',
    'http://sns-video-hw.xhscdn.com',
    'http://sns-video-al.xhscdn.com',
    'http://sns-video-tx.xhscdn.com',
    'http://sns-video-zl.xhscdn.com',
    'http://sns-video-v27.xhscdn.com',
    'http://sns-video-ali.xhscdn.com',
    'https://sns-video-bd.xhscdn.com',
    'https://sns-video-qc.xhscdn.com',
    'https://sns-video-hw.xhscdn.com',
    'https://sns-video-al.xhscdn.com',
    'https://sns-video-tx.xhscdn.com',
    'https://sns-video-zl.xhscdn.com'
]

headers = {
    'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1',
    'Referer': 'https://www.xiaohongshu.com/'
}

for d in domains:
    url = f"{d}/{key}"
    t0 = time.time()
    try:
        r = requests.get(url, headers=headers, stream=True, timeout=5)
        if r.status_code == 200:
            # Download first 2MB to measure speed
            buf = bytearray()
            for chunk in r.iter_content(256*1024):
                buf.extend(chunk)
                if len(buf) >= 2*1024*1024:
                    break
            dt = time.time() - t0
            speed_mb = (len(buf) / (1024*1024)) / dt if dt > 0 else 0
            print(f"Domain {d}: SUCCESS 200 - Speed: {speed_mb:.2f} MB/s in {dt:.2f}s")
        else:
            print(f"Domain {d}: Status {r.status_code}")
    except Exception as e:
        print(f"Domain {d}: Error {e}")
