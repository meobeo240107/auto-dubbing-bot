import requests

vid = "7645654329404136137"
urls_to_test = [
    f"https://www.iesdouyin.com/share/video/{vid}/",
    f"https://www.douyin.com/video/{vid}",
    f"https://www.iesdouyin.com/share/video/{vid}",
]

api_url = "https://www.tikwm.com/api/"
for u in urls_to_test:
    print(f"\nTesting TikWM with URL: {u}")
    try:
        r = requests.post(api_url, data={"url": u, "hd": 1}, timeout=10)
        data = r.json()
        print(" -> Code:", data.get("code"))
        if data.get("code") == 0:
            print(" -> SUCCESS! Title:", data["data"].get("title"))
            print(" -> Play:", data["data"].get("play"))
        else:
            print(" -> Error:", data.get("msg"))
    except Exception as e:
        print(" -> Exception:", e)

# Test other well-known free multi-downloader APIs
other_apis = [
    ("Tiktod API", f"https://api.tiktod.org/api/v1/douyin?url=https://www.iesdouyin.com/share/video/{vid}/"),
    ("SnapDouyin API", f"https://snapdouyin.app/api/ajaxSearch"),
    ("DLPanda API", f"https://dlpanda.com/api/douyin?url=https://www.douyin.com/video/{vid}"),
    ("LoveTik API", f"https://lovetik.com/api/ajax/search")
]

for name, api in other_apis:
    print(f"\nTesting {name}...")
    try:
        if "ajax" in api:
            r = requests.post(api, data={"q": f"https://www.iesdouyin.com/share/video/{vid}/"}, timeout=10)
        else:
            r = requests.get(api, timeout=10)
        print(f" -> {name} Status: {r.status_code}")
        print(" -> Response:", r.text[:200])
    except Exception as e:
        print(f" -> {name} Exception:", e)
