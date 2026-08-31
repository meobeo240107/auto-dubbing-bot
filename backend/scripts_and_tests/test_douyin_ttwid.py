import requests
import json

def get_ttwid():
    url = "https://ttwid.bytedance.com/rr/"
    data = {
        "region": "cn",
        "aid": 1768,
        "needFid": "0",
        "service": "www.ixigua.com",
        "migrate_info": {"ticket": "", "source": "node"},
        "cbUrlProtocol": "https",
        "union": True
    }
    try:
        r = requests.post(url, json=data, timeout=5)
        ttwid = r.cookies.get("ttwid")
        if ttwid:
            return ttwid
    except Exception as e:
        print("ttwid error:", e)
    return ""

ttwid = get_ttwid()
print("Generated ttwid:", ttwid)

if ttwid:
    vid = "7645654329404136137"
    api_url = f"https://www.douyin.com/aweme/v1/web/aweme/detail/?aweme_id={vid}&aid=1128&version_code=190500"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Referer": "https://www.douyin.com/",
        "Cookie": f"ttwid={ttwid};"
    }
    r = requests.get(api_url, headers=headers, timeout=10)
    print("API Status with ttwid:", r.status_code)
    try:
        data = r.json()
        aweme = data.get("aweme_detail", {})
        print("Title:", aweme.get("desc"))
        play_url = aweme.get("video", {}).get("play_addr", {}).get("url_list", [])
        print("Play URLs:", play_url)
    except Exception as e:
        print("Json error:", e)
