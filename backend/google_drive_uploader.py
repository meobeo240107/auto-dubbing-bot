"""
Module tự động tải video lên Google Drive sau khi render xong.
Hỗ trợ cả Service Account và OAuth 2.0 User Login.
"""

import os
import sys
import io
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any

# Fix Windows console UTF-8 encoding
if hasattr(sys.stdout, "reconfigure"):
    try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass
if hasattr(sys.stderr, "reconfigure"):
    try: sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass

logger = logging.getLogger(__name__)

DEFAULT_FOLDER_ID = "1N3VsuAwtaERsfLgAK6Zc7bOEF8B7qj5c"
SCOPES = ["https://www.googleapis.com/auth/drive.file", "https://www.googleapis.com/auth/drive"]

def get_gdrive_service():
    """Tạo hoặc lấy kết nối Google Drive API service."""
    from googleapiclient.discovery import build
    from google.oauth2 import service_account
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from google_auth_oauthlib.flow import InstalledAppFlow

    base_dir = Path(__file__).resolve().parent
    
    # 1. Thử Service Account JSON
    sa_paths = [
        base_dir / "gdrive_service_account.json",
        base_dir / "service_account.json",
        base_dir / "credentials.json",
        Path("C:/tool v2/backend/gdrive_service_account.json"),
    ]
    for sa in sa_paths:
        if sa.exists():
            try:
                creds = service_account.Credentials.from_service_account_file(str(sa), scopes=SCOPES)
                service = build("drive", "v3", credentials=creds)
                logger.info(f"Đã xác thực Google Drive bằng Service Account: {sa.name}")
                return service
            except Exception as e:
                logger.warning(f"Không thể nạp Service Account từ {sa}: {e}")

    # 2. Thử OAuth Token JSON
    token_path = base_dir / "gdrive_token.json"
    oauth_client_path = base_dir / "gdrive_oauth_client.json"
    
    creds = None
    if token_path.exists():
        try:
            creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
        except Exception:
            creds = None
            
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                with open(token_path, "w", encoding="utf-8") as token_file:
                    token_file.write(creds.to_json())
            except Exception as e:
                logger.warning(f"Lỗi refresh token: {e}")
                creds = None
        elif oauth_client_path.exists():
            try:
                flow = InstalledAppFlow.from_client_secrets_file(str(oauth_client_path), SCOPES)
                creds = flow.run_local_server(port=0)
                with open(token_path, "w", encoding="utf-8") as token_file:
                    token_file.write(creds.to_json())
            except Exception as e:
                logger.warning(f"Lỗi OAuth flow: {e}")
                creds = None

    if creds and creds.valid:
        return build("drive", "v3", credentials=creds)
        
    return None

def upload_video_to_gdrive(file_path: str | Path, folder_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Tải một file video lên Google Drive và trả về thông tin file."""
    file_path = Path(file_path)
    if not file_path.exists():
        logger.error(f"File không tồn tại: {file_path}")
        return None
        
    target_folder = folder_id or os.getenv("GDRIVE_FOLDER_ID", DEFAULT_FOLDER_ID)
    service = get_gdrive_service()
    if not service:
        logger.warning("Chưa cấu hình xác thực Google Drive API (cần gdrive_service_account.json hoặc gdrive_oauth_client.json)")
        return None
        
    try:
        from googleapiclient.http import MediaFileUpload
        file_name = file_path.name
        file_metadata = {
            "name": file_name,
            "parents": [target_folder] if target_folder else []
        }
        
        media = MediaFileUpload(str(file_path), mimetype="video/mp4", resumable=True)
        print(f"☁️ Đang tải {file_name} lên Google Drive (Folder ID: {target_folder})...", flush=True)
        
        request = service.files().create(body=file_metadata, media_body=media, fields="id, name, webViewLink, webContentLink")
        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                print(f"  Tải lên: {int(status.progress() * 100)}%", flush=True)
                
        file_id = response.get("id")
        web_link = response.get("webViewLink", f"https://drive.google.com/file/d/{file_id}/view")
        print(f"🎉 Tải lên Google Drive thành công!\n🔗 Link xem: {web_link}", flush=True)
        return {
            "id": file_id,
            "name": file_name,
            "link": web_link,
            "folder_id": target_folder
        }
    except Exception as e:
        logger.error(f"Lỗi khi tải file lên Google Drive: {e}")
        print(f"❌ Lỗi tải lên Google Drive: {e}", flush=True)
        return None

if __name__ == "__main__":
    if len(sys.argv) > 1:
        test_file = sys.argv[1]
        upload_video_to_gdrive(test_file)
    else:
        print("Sử dụng: python google_drive_uploader.py <duong_dan_file_video>")
