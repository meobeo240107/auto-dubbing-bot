import requests
import json

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Referer": "https://www.douyin.com/",
    "Accept": "application/json, text/plain, */*",
}

vid = "7645654329404136137"

# Method 1: iesdouyin iteminfo
print("Testing iesdouyin iteminfo...")
try:
    r = requests.get(f"https://www.iesdouyin.com/web/api/v2/aweme/iteminfo/?item_ids={vid}", headers=headers, timeout=10)
    print("Status:", r.status_code)
    print("Response:", r.text[:300])
except Exception as e:
    print("Error:", e)

# Method 2: douyin detail API
print("\nTesting douyin detail API...")
try:
    r = requests.get(f"https://www.douyin.com/aweme/v1/web/aweme/detail/?aweme_id={vid}", headers=headers, timeout=10)
    print("Status:", r.status_code)
    data = r.json()
    aweme = data.get("aweme_detail", {})
    print("Title:", aweme.get("desc"))
    video = aweme.get("video", {})
    play_addr = video.get("play_addr", {}).get("url_list", [])
    print("Play URLs:", play_addr)
    # Check if images (slideshow)
    images = aweme.get("images", [])
    print("Images count:", len(images))
except Exception as e:
    print("Error:", e)

# Method 3: test other free downloader APIs (like lovetik / ssstik / douyin.wtf / snapany)
print("\nTesting third-party APIs...")
apis = [
    f"https://api.douyin.wtf/api?url=https://www.douyin.com/video/{vid}",
    f"https://api.vvebo.com/api/douyin?url=https://www.douyin.com/video/{vid}"
]
for api in apis:
    try:
        r = requests.get(api, timeout=10)
        print(f"{api} -> {r.status_code}")
        print(r.text[:200])
    except Exception as e:
        print(f"Failed {api}: {e}")
