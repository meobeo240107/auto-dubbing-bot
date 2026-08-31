import requests
import re
import json

headers = {
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
}

vid = "7645654329404136137"
url = f"https://www.iesdouyin.com/share/video/{vid}/"

r = requests.get(url, headers=headers, timeout=10)
html = r.text

# Find script tags containing window data
scripts = re.findall(r'<script[^>]*>(.*?)</script>', html, re.DOTALL)
print("Total script tags:", len(scripts))
for i, s in enumerate(scripts):
    if len(s) > 100:
        print(f"\n--- Script {i} (len={len(s)}) ---")
        print(s[:300] + " ... " + s[-100:])
        if "router" in s.lower() or "init" in s.lower() or "video" in s.lower() or "aweme" in s.lower():
            print("  >> Matched keyword in script", i)
            # Try to find JSON
            match = re.search(r'=\s*(\{.*?\});?\s*$', s.strip(), re.DOTALL)
            if match:
                try:
                    data = json.loads(match.group(1))
                    print("  Parsed JSON successfully!")
                    with open("douyin_script_data.json", "w", encoding="utf-8") as f:
                        json.dump(data, f, ensure_ascii=False, indent=2)
                except Exception as e:
                    print("  JSON parse error:", e)
