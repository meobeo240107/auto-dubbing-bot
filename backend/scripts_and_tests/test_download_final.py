import os
import sys

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from social_downloader import download_social_video

url = 'http://xhslink.com/o/2stbyFrGqXe'
output_dir = 'workspace/downloads'
prefix = 'test_verify_nowatermark'

ok, vpath, title, err = download_social_video(url, output_dir, prefix)
print(f"Result ok={ok}")
print(f"Path: {vpath}")
print(f"Title: {title}")
print(f"Size: {os.path.getsize(vpath) if os.path.exists(vpath) else 0} bytes")
