import requests
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

key = 'pre_post/1040g0cg31v7mhfmp3m005nq25i308pb8e0770co'
domains = [
    'http://sns-video-qc.xhscdn.com',
    'http://sns-video-bd.xhscdn.com',
    'http://sns-video-hw.xhscdn.com',
    'http://sns-video-al.xhscdn.com',
    'http://sns-video-v27.xhscdn.com',
    'http://sns-video-s10.xhscdn.com',
    'https://sns-video-qc.xhscdn.com',
    'https://sns-video-bd.xhscdn.com',
    'https://sns-video-hw.xhscdn.com',
    'https://sns-video-al.xhscdn.com'
]
headers = {'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1'}
for d in domains:
    url = f'{d}/{key}'
    try:
        r = requests.head(url, headers=headers, timeout=5)
        print(f'{url} -> Status: {r.status_code}, Length: {r.headers.get("Content-Length")}')
    except Exception as e:
        print(f'{url} -> Error: {e}')
