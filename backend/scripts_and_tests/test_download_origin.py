import requests
import json
import os
import ffmpeg

key = 'pre_post/1040g0cg31v7mhfmp3m005nq25i308pb8e0770co'
url = f'http://sns-video-bd.xhscdn.com/{key}'
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'}

dest = 'test_no_watermark.mp4'
print(f"Downloading {url}...")
with requests.get(url, headers=headers, stream=True) as r:
    r.raise_for_status()
    with open(dest, 'wb') as f:
        for chunk in r.iter_content(chunk_size=1024*1024):
            if chunk: f.write(chunk)

print(f"Downloaded size: {os.path.getsize(dest)} bytes")
probe = ffmpeg.probe(dest)
v_stream = next(s for s in probe['streams'] if s['codec_type'] == 'video')
print(f"Video resolution: {v_stream['width']}x{v_stream['height']}, codec: {v_stream['codec_name']}")
