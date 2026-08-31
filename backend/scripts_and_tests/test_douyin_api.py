import requests
import json

def test_tikwm(douyin_url):
    api_url = "https://www.tikwm.com/api/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    params = {"url": douyin_url, "hd": 1}
    try:
        res = requests.post(api_url, data=params, headers=headers, timeout=15)
        data = res.json()
        print("Status code:", res.status_code)
        print("Response data keys:", data.keys() if isinstance(data, dict) else data)
        if data.get("code") == 0:
            print("Title:", data["data"].get("title"))
            print("Play URL (No Watermark):", data["data"].get("play"))
            print("HD Play URL:", data["data"].get("hdplay"))
            return True
        else:
            print("Error message:", data.get("msg"))
            return False
    except Exception as e:
        print("Exception:", e)
        return False

if __name__ == "__main__":
    # Test with standard domain check
    print("Testing TikWM API reachability...")
    test_tikwm("https://v.douyin.com/iJabcdef/")
