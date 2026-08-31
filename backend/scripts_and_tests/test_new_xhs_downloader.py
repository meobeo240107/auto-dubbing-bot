import os
import re
import json
import requests
import sys

sys.stdout.reconfigure(encoding='utf-8')

USER_AGENTS = {
    "mobile": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
    "desktop": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
}

def clean_filename(title: str, max_len: int = 40) -> str:
    if not title:
        return "xhs_video"
    # Lọc bỏ ký tự cấm trên Windows và các emoji phức tạp
    cleaned = re.sub(r'[\\/*?:"<>|]', '', title).strip()
    cleaned = re.sub(r'[^\w\s\u4e00-\u9fff\u3040-\u30ff\uac00-\ud7af\-_.]', '', cleaned)
    cleaned = re.sub(r'\s+', '_', cleaned)
    return cleaned[:max_len] or "xhs_video"

def download_file_stream(url: str, dest_path: str, headers: dict = None, timeout: int = 60) -> bool:
    try:
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        req_headers = headers or {"User-Agent": USER_AGENTS["desktop"]}
        with requests.get(url, headers=req_headers, stream=True, timeout=timeout) as response:
            response.raise_for_status()
            with open(dest_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        f.write(chunk)
        return os.path.exists(dest_path) and os.path.getsize(dest_path) > 10000
    except Exception as e:
        print(f"Stream error: {e}")
        if os.path.exists(dest_path):
            try: os.remove(dest_path)
            except: pass
        return False

def download_xiaohongshu(url: str, output_dir: str, prefix: str) -> tuple:
    os.makedirs(output_dir, exist_ok=True)
    try:
        headers = {
            'User-Agent': USER_AGENTS["mobile"],
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8'
        }
        res = requests.get(url, headers=headers, allow_redirects=True, timeout=15)
        real_url = res.url
        
        # Kiểm tra nếu link đã bị xóa / hết hạn (XHS redirect về trang chủ)
        if real_url.rstrip('/') in ["https://www.xiaohongshu.com", "http://www.xiaohongshu.com", "https://xiaohongshu.com"]:
            return False, "", "", "Bài viết trên Tiểu Hồng Thư (XHS) này đã bị xóa hoặc link không tồn tại"

        html = res.text
        if "你访问的页面不见了" in html or "页面不存在" in html:
            return False, "", "", "Bài viết trên Tiểu Hồng Thư này đã bị tác giả xóa (Trang không tồn tại)"

        video_url = None
        title = "xiaohongshu_video"

        # 1. Trích xuất từ window.__INITIAL_STATE__
        state_match = re.search(r'window\.__INITIAL_STATE__\s*=\s*(\{.*?\})</script>', html, re.DOTALL)
        if state_match:
            try:
                raw_json = state_match.group(1).replace("undefined", "null")
                state = json.loads(raw_json)
                note_data = state.get("noteData", {}).get("data", {}).get("noteData", {})
                title = note_data.get("title") or note_data.get("desc", "") or "xhs_video"
                
                video = note_data.get("video")
                if video and isinstance(video, dict):
                    media = video.get("media", {})
                    stream = media.get("stream", {})
                    # Ưu tiên h264 -> h265 -> av1
                    for st_type in ['h264', 'h265', 'av1', 'h266']:
                        st_list = stream.get(st_type, [])
                        if st_list and isinstance(st_list, list):
                            for item in st_list:
                                video_url = item.get("masterUrl") or item.get("url")
                                if not video_url:
                                    backups = item.get("backupUrls", [])
                                    if backups:
                                        video_url = backups[0]
                                if video_url:
                                    break
                        if video_url:
                            break
            except Exception as e:
                print(f"JSON extract error: {e}")

        # 2. Dự phòng: Regex quét trực tiếp url mp4 / m3u8
        if not video_url:
            video_matches = re.findall(r'http[s]?://[^\s"\'<>]+\.(?:mp4|m3u8)[^\s"\'<>]*', html)
            for v in video_matches:
                if "sns-video" in v or "xhscdn" in v or "spectrum" in v:
                    video_url = v.replace(r'\u002F', '/')
                    break

        if video_url:
            safe_title = clean_filename(title)
            target_path = os.path.join(output_dir, f"{prefix}_{safe_title}.mp4")
            if download_file_stream(video_url, target_path, headers=headers):
                return True, target_path, title, ""

        # Nếu là bài đăng toàn ảnh (không có video)
        if state_match and "imageList" in str(state_match.group(1)):
            return False, "", "", "Bài viết này là Album ảnh (không phải video)"

        return False, "", "", "Không tìm thấy luồng video trong bài viết Tiểu Hồng Thư"
    except Exception as e:
        return False, "", "", f"Lỗi bóc tách XHS: {str(e)}"

# Test với các link
test_links = [
    'http://xhslink.com/o/12IgoDtwFtm',
    'http://xhslink.com/o/ATdSTNcDts',
    'http://xhslink.com/o/8ea48HPIQU3',
    'http://xhslink.com/o/7Jnsrl1mohO'
]

for link in test_links:
    print(f"\n--- Testing: {link} ---")
    ok, path, title, err = download_xiaohongshu(link, "test_out_dir", "test")
    print(f"Success: {ok}")
    print(f"Title: {title}")
    print(f"Path: {path}")
    print(f"Size: {os.path.getsize(path) if ok and os.path.exists(path) else 0} bytes")
    print(f"Error: {err}")
