import os
import json
import requests
import base64
import re
from deep_translator import GoogleTranslator
import logging

logger = logging.getLogger(__name__)

def translate_with_gemini(
    texts,
    target_lang="vi",
    api_key="",
    video_path=None,
    context_start_seconds=None,
    context_end_seconds=None,
    prior_context=None,
):
    if not api_key:
        return None
    try:
        lang_name = "Tiếng Việt" if target_lang == "vi" else target_lang
        prompt = f"""Bạn là một chuyên gia dịch thuật nội dung mạng xã hội (Tiktok, Douyin).
Nhiệm vụ: Dịch mảng JSON chứa các câu phụ đề dưới đây sang {lang_name}.
Yêu cầu TỐI QUAN TRỌNG:
1. BẮT BUỘC giữ nguyên số lượng phần tử của mảng JSON. Mỗi câu gốc tương ứng đúng 1 câu dịch. Không tự ý gộp câu hay tách câu để đảm bảo khớp thời gian hiển thị (timing).
2. DỊCH CHUẨN XÁC NHƯNG HẤP DẪN: Ưu tiên dịch đúng nghĩa đen và bóng của câu chữ. Giữ văn phong tự nhiên, cuốn hút, có chút thiên hướng mạng xã hội để đăng video.
3. XỬ LÝ TỪ NGỮ VĂN HOA/THƠ CA: Các video Douyin thường dùng câu chữ hoa mỹ. Ví dụ '懒春秋' mang ý nghĩa 'thư thái, nhàn hạ' chứ KHÔNG PHẢI là 'lười biếng'. Hãy dịch thoát ý, sang trọng.
4. TUYỆT ĐỐI KHÔNG lạm dụng từ tiếng Anh. Ưu tiên tiếng Việt thuần túy.
5. Ngắn gọn & Súc tích: Văn bản dịch dùng để lồng tiếng (TTS), độ dài câu dịch phải tương đương câu gốc để AI đọc không bị tua quá nhanh.
6. Ngữ cảnh nối tiếp: Vì phụ đề thường bị ngắt giữa chừng, hãy đọc cả đoạn để dịch sao cho ý nối liền mạch trơn tru.
7. TRỰC QUAN: Hãy kết hợp 5 bức ảnh đính kèm từ video để chọn đại từ nhân xưng và danh từ chính xác tuyệt đối với ngữ cảnh.
8. CHỈ trả về mảng JSON chứa các chuỗi dịch, không giải thích, không markdown.
Dữ liệu:
"""
        if prior_context:
            prompt += "Ngữ cảnh nối tiếp từ batch trước (không dịch lại):\n"
            prompt += json.dumps(prior_context, ensure_ascii=False) + "\n"
        prompt += json.dumps(texts, ensure_ascii=False)
        
        parts = [{"text": prompt}]
        
        if video_path and os.path.exists(video_path):
            try:
                import cv2
                cap = cv2.VideoCapture(video_path)
                total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                num_frames = 5
                if (
                    context_start_seconds is not None
                    and context_end_seconds is not None
                    and float(context_end_seconds) > float(context_start_seconds)
                ):
                    start = max(0.0, float(context_start_seconds))
                    span = float(context_end_seconds) - start
                    positions = [
                        ("msec", (start + span * i / (num_frames + 1)) * 1000.0)
                        for i in range(1, num_frames + 1)
                    ]
                elif total_frames > 0:
                    step = max(total_frames // (num_frames + 1), 1)
                    positions = [
                        ("frame", i * step) for i in range(1, num_frames + 1)
                    ]
                else:
                    positions = []
                for position_type, position in positions:
                    if position_type == "msec":
                        cap.set(cv2.CAP_PROP_POS_MSEC, position)
                    else:
                        cap.set(cv2.CAP_PROP_POS_FRAMES, position)
                    ret, frame = cap.read()
                    if ret:
                        _, buffer = cv2.imencode('.jpg', frame)
                        b64_str = base64.b64encode(buffer).decode('utf-8')
                        parts.append({
                            "inline_data": {
                                "mime_type": "image/jpeg",
                                "data": b64_str
                            }
                        })
                cap.release()
                print("Đã đính kèm ảnh từ video vào prompt để Gemini hiểu ngữ cảnh.")
            except Exception as img_e:
                print(f"Không thể trích xuất ảnh từ video: {img_e}")
        
        models_to_try = ["gemini-3.7-flash", "gemini-3.6-flash", "gemini-3.5-flash", "gemini-3.5-flash-lite"]
        response = None
        
        for model in models_to_try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
            payload = {"contents": [{"parts": parts}]}
            headers = {"Content-Type": "application/json"}
            
            try:
                print(f"Đang thử gọi mô hình Gemini: {model}...")
                response = requests.post(url, json=payload, headers=headers, timeout=60)
                if response.status_code == 200:
                    print(f"Gọi thành công mô hình {model}!")
                    break
                else:
                    print(f"Lỗi gọi {model} (HTTP {response.status_code}) - Chuyển sang phương án dự phòng...")
            except Exception as req_e:
                print(f"Lỗi kết nối khi gọi {model}: {req_e} - Chuyển sang phương án dự phòng...")
                
        if not response or response.status_code != 200:
            print("Đã thử tất cả các mô hình Gemini dự phòng nhưng đều thất bại.")
            return None
            
        result = response.json()
        try:
            text = result["candidates"][0]["content"]["parts"][0]["text"].strip()
        except KeyError:
            print("Lỗi parse phản hồi Gemini.")
            return None
        
        match = re.search(r'\[.*\]', text, re.DOTALL)
        if match:
            text = match.group(0)
            
        translated = json.loads(text)
        if len(translated) == len(texts):
            return translated
    except Exception as e:
        print(f"Lỗi dịch Gemini: {e}", flush=True)
    return None

def translate_with_g4f(texts, target_lang="vi"):
    try:
        import g4f
        lang_name = "Tiếng Việt" if target_lang == "vi" else target_lang
        prompt = f"""Bạn là một chuyên gia dịch thuật nội dung mạng xã hội (Tiktok, Douyin).
Nhiệm vụ: Dịch mảng JSON chứa các câu phụ đề dưới đây sang {lang_name}.
Yêu cầu TỐI QUAN TRỌNG:
1. BẮT BUỘC giữ nguyên số lượng phần tử của mảng JSON.
2. Dịch tự nhiên, cuốn hút, chuẩn văn phong video ngắn mạng xã hội.
3. CHỈ trả về mảng JSON chứa các chuỗi dịch, không giải thích, không markdown.
Dữ liệu:
"""
        prompt += json.dumps(texts, ensure_ascii=False)
        
        fallback_models = ["gpt-4o", "deepseek-v3", "claude-3.5-sonnet"]
        for g4f_model in fallback_models:
            try:
                print(f"Đang gọi mô hình AI miễn phí {g4f_model} qua G4F...")
                response = g4f.ChatCompletion.create(
                    model=g4f_model,
                    messages=[{"role": "user", "content": prompt}]
                )
                
                text = response.strip()
                match = re.search(r'\[[\s\S]*\]', text)
                if match:
                    text = match.group(0)
                    
                translated = json.loads(text)
                if len(translated) == len(texts):
                    print(f"Dịch thành công bằng mô hình {g4f_model}!")
                    return translated
            except Exception as m_err:
                print(f"Mô hình {g4f_model} gặp lỗi: {m_err}")
    except Exception as e:
        print(f"Lỗi dịch G4F: {e}", flush=True)
    return None

def translate_subtitles(
    srt_segments,
    target_lang="vi",
    api_key="",
    video_path=None,
    context_start_seconds=None,
    context_end_seconds=None,
    prior_context=None,
):
    print("Translating subtitles...")
    texts = [seg.content for seg in srt_segments if seg.content]
    translated_texts = None
    
    if api_key and texts:
        print("Trying Gemini API...")
        translated_texts = translate_with_gemini(
            texts,
            target_lang,
            api_key,
            video_path,
            context_start_seconds=context_start_seconds,
            context_end_seconds=context_end_seconds,
            prior_context=prior_context,
        )
        
    if not translated_texts and texts:
        print("Trying ChatGPT (G4F) API...")
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(translate_with_g4f, texts, target_lang)
            try:
                translated_texts = future.result(timeout=40)
            except concurrent.futures.TimeoutError:
                print("G4F phản hồi quá lâu (quá 40s), hủy để tránh treo bot.")
                translated_texts = None
            except Exception as e:
                print(f"Lỗi G4F: {e}")
                translated_texts = None
        
    if translated_texts:
        idx = 0
        for segment in srt_segments:
            if not segment.content:
                continue
            segment.orig_content = segment.content
            segment.content = translated_texts[idx]
            idx += 1
        print("Gemini translation successful.")
        return srt_segments
    
    print("Falling back to Google Translate...")
    for segment in srt_segments:
        if not segment.content:
            continue
            
        try:
            segment.orig_content = segment.content
            translator = GoogleTranslator(source='auto', target=target_lang)
            translated_text = translator.translate(segment.content)
            
            if translated_text == segment.content and any('\u4e00' <= c <= '\u9fff' for c in segment.content):
                zh_translator = GoogleTranslator(source='zh-CN', target=target_lang)
                translated_text = zh_translator.translate(segment.content)
            
            if "Error 500" in translated_text or "Server Error" in translated_text or translated_text.startswith("Error"):
                logger.warning(f"Google Translate trả về lỗi rác: {translated_text}")
                translated_text = segment.content
                
        except Exception as e:
            print(f"Lỗi dịch thuật: {e}")
            translated_text = segment.content
            
        segment.content = translated_text
        
    return srt_segments
