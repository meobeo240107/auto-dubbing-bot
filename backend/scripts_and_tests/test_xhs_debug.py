import requests
import re
import json

url = 'http://xhslink.com/o/12IgoDtwFtm'
headers = {
    'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8'
}
r = requests.get(url, headers=headers, allow_redirects=True, timeout=15)
print("Final URL:", r.url)
print("Status Code:", r.status_code)
print("HTML length:", len(r.text))

# Save html for inspection
with open("xhs_sample.html", "w", encoding="utf-8") as f:
    f.write(r.text)

# Check for INITIAL_STATE
state_match = re.search(r'window\.__INITIAL_STATE__\s*=\s*(\{.*?\})</script>', r.text, re.DOTALL)
if state_match:
    print("Found __INITIAL_STATE__!")
    try:
        raw_json = state_match.group(1).replace("undefined", "null")
        data = json.loads(raw_json)
        print("Keys in state:", list(data.keys()))
        with open("xhs_state.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print("JSON parse error:", e)
else:
    print("No __INITIAL_STATE__ found.")
    # Search for video URLs
    v_urls = re.findall(r'http[s]?://[^\s"\'<>]+\.mp4[^\s"\'<>]*', r.text)
    print("Direct mp4 matches:", len(v_urls), v_urls[:3])
