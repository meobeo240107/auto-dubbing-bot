import requests
import json
import re

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Referer": "https://www.douyin.com/",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}

vid = "7645654329404136137"

session = requests.Session()
session.headers.update(headers)

# 1. Visit douyin to obtain guest cookies (__ac_nonce, ttwid, etc.)
print("1. Fetching guest cookies from Douyin homepage...")
r0 = session.get("https://www.douyin.com/", timeout=10)
cookies = session.cookies.get_dict()
print("Cookies obtained:", cookies.keys())

# 2. Now request the video page directly or the detail API
print("\n2. Requesting video page...")
video_url = f"https://www.douyin.com/video/{vid}"
r1 = session.get(video_url, timeout=10)
print("Video page status:", r1.status_code)

# Check if RENDER_DATA or router data is inside html
if "RENDER_DATA" in r1.text or "_ROUTER_DATA" in r1.text:
    print("Found embedded JSON data in HTML!")
    # Find JSON
    match = re.search(r'<script id="RENDER_DATA" type="application/json">(.+?)</script>', r1.text)
    if match:
        import urllib.parse
        raw_json = urllib.parse.unquote(match.group(1))
        data = json.loads(raw_json)
        print("RENDER_DATA keys:", data.keys() if isinstance(data, dict) else type(data))

# 3. Test TikWM with cookies or test TikHub/Douyin direct API
print("\n3. Testing detail API with fresh session...")
detail_url = f"https://www.douyin.com/aweme/v1/web/aweme/detail/?aweme_id={vid}&aid=1128&version_code=190500"
r2 = session.get(detail_url, timeout=10)
print("Detail API status:", r2.status_code)
try:
    data2 = r2.json()
    print("Detail API response keys:", data2.keys())
    aweme = data2.get("aweme_detail", {})
    if aweme:
        print("Video title:", aweme.get("desc"))
        play_list = aweme.get("video", {}).get("play_addr", {}).get("url_list", [])
        print("Play URLs:", play_list)
except Exception as e:
    print("Detail API json error:", e, r2.text[:200])
