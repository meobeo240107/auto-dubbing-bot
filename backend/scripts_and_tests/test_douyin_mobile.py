import requests
import re
import json

headers = {
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9",
}

vid = "7645654329404136137"
url = f"https://www.iesdouyin.com/share/video/{vid}/"

print(f"Requesting {url} with mobile UA...")
r = requests.get(url, headers=headers, allow_redirects=True, timeout=10)
print("Status:", r.status_code)
print("Final URL:", r.url)

# Search for video src or _ROUTER_DATA
html = r.text
print("HTML length:", len(html))

# Look for video play url in html
urls = re.findall(r'https?://[^\s"\'<>]+\.(?:mp4|m3u8)[^\s"\'<>]*', html)
print("MP4/M3U8 URLs found in HTML:", len(urls))
for u in urls[:5]:
    print(" ->", u)

# Search for play_addr or video src
matches = re.findall(r'play_addr\s*":\s*{\s*"url_list"\s*:\s*\[\s*"([^"]+)"', html)
print("play_addr matches:", len(matches))
for m in matches:
    print(" -> play_addr:", m.replace(r'\u002F', '/'))

matches2 = re.findall(r'<video[^>]+src=["\']([^"\']+)["\']', html)
print("Video tag src:", matches2)
