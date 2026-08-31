import requests
import json
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')

url = 'https://www.xiaohongshu.com/discovery/item/6a78495e0000000033032c03?app_platform=ios&app_version=9.41.2&share_from_user_hidden=true&xsec_source=app_share&type=video&xsec_token=CBRQD7yHIw-4I56N8R6JO5f9_YD_H3ttAKobUR3s9xqIE=&author_share=1&xhsshare=CopyLink&shareRedId=OD5DNDNJNjo2NzUyOTgwNjc8OThKPkdL&apptime=1787201155&share_id=f18a69c1e30c460b96f3233b85a14a0d'

headers = {
    'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
}

res = requests.get(url, headers=headers, allow_redirects=True, timeout=15)
state_match = re.search(r'window\.__INITIAL_STATE__\s*=\s*(\{.*?\})</script>', res.text, re.DOTALL)
if state_match:
    raw_json = state_match.group(1).replace("undefined", "null")
    state = json.loads(raw_json)
    note_data = state.get("noteData", {}).get("data", {}).get("noteData", {})
    video = note_data.get("video", {})
    print("=== FULL VIDEO OBJECT ===")
    print(json.dumps(video, ensure_ascii=False, indent=2))
