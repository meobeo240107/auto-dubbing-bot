import re
import requests
import json

def extract_douyin_video_id(url: str) -> str:
    """Trích xuất ID video Douyin từ bất kỳ định dạng link web nào"""
    # 1. Tìm modal_id hoặc aweme_id hoặc item_id trong query params
    query_match = re.search(r'(?:modal_id|aweme_id|item_id|item_ids|video_id)=(\d+)', url)
    if query_match:
        return query_match.group(1)
        
    # 2. Tìm /video/123456 hoặc /note/123456
    path_match = re.search(r'/(?:video|note)/(\d+)', url)
    if path_match:
        return path_match.group(1)
        
    # 3. Nếu là shortlink v.douyin.com
    if "v.douyin.com" in url:
        try:
            headers = {"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1"}
            res = requests.get(url, headers=headers, allow_redirects=True, timeout=10)
            sub_match = re.search(r'/(?:video|note)/(\d+)', res.url) or re.search(r'modal_id=(\d+)', res.url)
            if sub_match:
                return sub_match.group(1)
        except Exception as e:
            print(f"Error redirecting: {e}")
            
    return ""

test_url = "https://www.douyin.com/jingxuan/search/unboxing%20review?aid=068cdea8-6474-4d46-b2ef-a5f696329ef5&modal_id=7645654329404136137&type=general"
vid = extract_douyin_video_id(test_url)
print(f"Extracted Video ID: {vid}")

clean_url = f"https://www.douyin.com/video/{vid}"
print(f"Clean Canonical URL: {clean_url}")

# Test TikWM with clean canonical url
api_url = "https://www.tikwm.com/api/"
res = requests.post(api_url, data={"url": clean_url, "hd": 1}, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
data = res.json()
print("TikWM code:", data.get("code"))
if data.get("code") == 0:
    print("Video Title:", data["data"].get("title"))
    print("HD Video Play URL:", data["data"].get("hdplay") or data["data"].get("play"))
else:
    print("TikWM error:", data.get("msg"))
