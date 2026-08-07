import os
import asyncio
from faster_whisper import WhisperModel
from deep_translator import GoogleTranslator
import edge_tts
import srt
from datetime import timedelta
from pydub import AudioSegment

def extract_subtitles_whisper(audio_path, output_srt_path):
    print(f"Transcribing {audio_path}...")
    import torch, gc
    if torch.cuda.is_available():
        print(f"🚀 CUDA detected: {torch.cuda.get_device_name(0)}. Loading Whisper Large-v3...")
        model = WhisperModel("large-v3", device="cuda", compute_type="int8_float16")
    else:
        print("⚠️ Loading Whisper Large-v3 on CPU...")
        model = WhisperModel("large-v3", device="cpu", compute_type="int8")
        
    try:
        segments, info = model.transcribe(audio_path, beam_size=5)
        
        merged_segments = []
        current_segment = None
        
        for segment in segments:
            text = segment.text.strip()
            if not text:
                continue
                
            if current_segment is None:
                current_segment = {
                    "start": segment.start,
                    "end": segment.end,
                    "text": text
                }
            else:
                gap = segment.start - current_segment["end"]
                duration = segment.end - current_segment["start"]
                
                # Chú ý: Đã bỏ tính năng "Siêu gộp" theo yêu cầu để text không bị dài 5-6 dòng.
                # Chỉ gộp nếu câu quá ngắn (< 3 giây) và khoảng cách rất nhỏ (< 0.5 giây) để tránh sub 1 chữ rác.
                if gap < 0.5 and duration < 3.0:
                    current_segment["end"] = segment.end
                    current_segment["text"] += " " + text
                else:
                    merged_segments.append(current_segment)
                    current_segment = {
                        "start": segment.start,
                        "end": segment.end,
                        "text": text
                    }
                    
        if current_segment is not None:
            merged_segments.append(current_segment)
        
        srt_segments = []
        for i, seg in enumerate(merged_segments, start=1):
            sub = srt.Subtitle(
                index=i,
                start=timedelta(seconds=seg["start"]),
                end=timedelta(seconds=seg["end"]),
                content=seg["text"].strip()
            )
            srt_segments.append(sub)
        
        with open(output_srt_path, "w", encoding="utf-8") as f:
            f.write(srt.compose(srt_segments))
        
        return srt_segments
    finally:
        del model
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        print("🧹 Đã giải phóng bộ nhớ RAM/VRAM của Whisper AI.")

def translate_with_gemini(texts, target_lang="vi", api_key="", video_path=None):
    import json
    if not api_key:
        return None
    try:
        import requests
        import base64
        
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
        prompt += json.dumps(texts, ensure_ascii=False)
        
        parts = [{"text": prompt}]
        
        if video_path and os.path.exists(video_path):
            try:
                import cv2
                cap = cv2.VideoCapture(video_path)
                total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                if total_frames > 0:
                    num_frames = 5
                    step = max(total_frames // (num_frames + 1), 1)
                    for i in range(1, num_frames + 1):
                        cap.set(cv2.CAP_PROP_POS_FRAMES, i * step)
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
        
        # Sắp xếp theo thứ tự ưu tiên: mới nhất -> cũ hơn
        models_to_try = ["gemini-3.6-flash", "gemini-3.5-flash", "gemini-3.5-flash-lite", "gemini-3.1-flash-lite", "gemini-2.5-flash"]
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
        
        # Bắt mảng JSON một cách an toàn nhất
        import re
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
    import json
    try:
        import g4f
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
7. CHỈ trả về mảng JSON chứa các chuỗi dịch, không giải thích, không markdown.
Dữ liệu:
"""
        prompt += json.dumps(texts, ensure_ascii=False)
        
        print("Đang gọi ChatGPT (GPT-4o) qua G4F...")
        response = g4f.ChatCompletion.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}]
        )
        
        text = response.strip()
        import re
        match = re.search(r'\[.*\]', text, re.DOTALL)
        if match:
            text = match.group(0)
            
        translated = json.loads(text)
        if len(translated) == len(texts):
            return translated
    except Exception as e:
        print(f"Lỗi dịch G4F (ChatGPT): {e}", flush=True)
    return None

def translate_subtitles(srt_segments, target_lang="vi", api_key="", video_path=None):
    print("Translating subtitles...")
    translated_segments = []
    
    texts = [seg.content for seg in srt_segments if seg.content]
    translated_texts = None
    
    if api_key and texts:
        print("Trying Gemini API...")
        translated_texts = translate_with_gemini(texts, target_lang, api_key, video_path)
        
    # Bật lại G4F (ChatGPT-4o miễn phí) nhưng có màng lọc chống đơ bot (timeout 40s)
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
            
            # Google Auto đôi khi bị kẹt không dịch tiếng Trung, nếu vậy ta ép dịch tiếng Trung
            if translated_text == segment.content and any('\u4e00' <= c <= '\u9fff' for c in segment.content):
                zh_translator = GoogleTranslator(source='zh-CN', target=target_lang)
                translated_text = zh_translator.translate(segment.content)
            
            # Chặn lỗi HTML rác từ Google Translate (như Error 500, Server Error)
            if "Error 500" in translated_text or "Server Error" in translated_text or translated_text.startswith("Error"):
                logger.warning(f"Google Translate trả về lỗi rác: {translated_text}")
                translated_text = segment.content
                
        except Exception as e:
            print(f"Lỗi dịch thuật: {e}")
            translated_text = segment.content
            
        segment.content = translated_text
        
    return srt_segments

def save_srt(srt_segments, output_path):
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(srt.compose(srt_segments, reindex=False))

edge_semaphore = asyncio.Semaphore(3)

async def generate_tts_edge(text, output_path, voice="vi-VN-HoaiMyNeural", rate="+0%", pitch="+0Hz"):
    import asyncio
    async with edge_semaphore:
        communicate = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
        await asyncio.wait_for(communicate.save(output_path), timeout=25.0)

class FPTQuotaError(Exception): pass

async def generate_tts_fpt(text, output_path, api_key, voice="banmai", speed="0"):
    import httpx
    import asyncio
    
    url = "https://api.fpt.ai/hmi/tts/v5"
    headers = {
        "api-key": api_key,
        "voice": voice,
        "speed": speed,
        "format": "mp3"
    }
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(url, headers=headers, content=text.encode('utf-8'))
        
        if response.status_code == 200:
            result = response.json()
            if str(result.get("error")) != "0":
                if "quota" in str(result.get("message")).lower() or str(result.get("error")) == "1":
                    raise FPTQuotaError(f"Hết dung lượng FPT.AI hoặc lỗi: {result.get('message')}")
                raise Exception(f"FPT API Lỗi: {result.get('message')}")
                
            audio_url = result.get("async")
            if not audio_url:
                raise Exception("Không tìm thấy link async trong phản hồi FPT API")
                
            # Chờ hệ thống FPT gen audio (polling)
            for _ in range(30):
                await asyncio.sleep(2.0)
                try:
                    audio_res = await client.get(audio_url, timeout=15.0)
                    # Nếu status_code = 200 (OK), nội dung trả về là audio byte
                    if audio_res.status_code == 200 and "application/json" not in audio_res.headers.get("Content-Type", ""):
                        with open(output_path, "wb") as f:
                            f.write(audio_res.content)
                        return
                except Exception as e:
                    pass
        elif response.status_code in [401, 403, 429]:
            raise FPTQuotaError(f"Lỗi API Key FPT hoặc hết dung lượng/rate limit ({response.status_code})")
        else:
            raise Exception(f"Lỗi kết nối FPT API: {response.status_code}")

async def generate_tts_external(text, output_path, source="elevenlabs", api_key=""):
    """
    Giả lập gọi API bên ngoài (ElevenLabs, Viettel).
    """
    print(f"Calling {source} API with key {api_key[:4]}...")
    await generate_tts_edge(text, output_path, "vi-VN-HoaiMyNeural")

rvc_semaphore = asyncio.Semaphore(1)
global_rvc_instance = None
global_rvc_model_path = None

async def apply_rvc_clone(input_audio, output_audio, model_path):
    """
    Sử dụng RVC-Python để chuyển đổi giọng nói qua CUDA.
    Nạp model vào RAM 1 lần duy nhất để tối ưu tốc độ x100.
    """
    async with rvc_semaphore:
        print(f"Applying RVC model from {model_path} to {input_audio}...")
        import asyncio
        import traceback
        try:
            from rvc_python.infer import RVCInference
            
            def run_rvc():
                global global_rvc_instance, global_rvc_model_path
                if global_rvc_instance is None or global_rvc_model_path != model_path:
                    print("=> Nap model RVC vao VRAM (Chi chay 1 lan duy nhat)...")
                    global_rvc_instance = RVCInference(device="cuda:0")
                    index_path = model_path.replace(".pth", ".index")
                    if os.path.exists(index_path):
                        print(f"=> Da tim thay file Index: {index_path}")
                        global_rvc_instance.load_model(model_path, version="v2", index_path=index_path)
                    else:
                        print("=> Khong tim thay file Index, giong doc co the kem tu nhien.")
                        global_rvc_instance.load_model(model_path, version="v2")
                    global_rvc_model_path = model_path
                # Cấu hình RVC - Tối ưu cho giọng thực tế của user:
                # - f0up_key=4: Nâng 4 tone.
                # - index_rate=0.5: Lấy 50% màu giọng user + 50% độ rõ chữ giọng mồi để không bị lơ lớ.
                # - protect=0.1: Giữ rõ các phụ âm đầu tiếng Việt (th, tr, ch...).
                global_rvc_instance.set_params(f0up_key=4, f0method="rmvpe", index_rate=0.5, protect=0.1, filter_radius=3, rms_mix_rate=0.25)
                global_rvc_instance.infer_file(input_audio, output_audio)
                
            await asyncio.to_thread(run_rvc)
            print(f"=> RVC Cloning Successful cho file {output_audio}")
            
        except Exception as e:
            print(f"=> Loi khi chay RVC: {e}")
            traceback.print_exc()
            import shutil
            shutil.copy(input_audio, output_audio)

async def generate_audio_tts(text, output_path, voice_source="edge", voice_param="vi-VN-HoaiMyNeural"):
    """
    Tạo giọng đọc từ văn bản tiếng Việt.
    - voice_source="edge": Microsoft Edge Neural TTS
    - voice_source="google": Google Translate TTS (Chị Google)
    """
    # Lọc bỏ các ký tự đặc biệt, chỉ giữ lại chữ cái và số để TTS không bị lỗi
    clean_text = re.sub(r'[^\w\s\.\,\!\?]', '', text).strip()
    if not clean_text or not any(c.isalnum() for c in clean_text):
        raise ValueError(f"NoAudioReceived: Đoạn văn bản chỉ chứa ký tự đặc biệt hoặc trống ({text})")

    if voice_source == "edge":
        communicate = edge_tts.Communicate(clean_text, voice_param)
        await communicate.save(output_path)
        return output_path
    elif voice_source == "google":
        from gtts import gTTS
        # gTTS chạy đồng bộ, nên có thể gói vào thread hoặc chạy thẳng nếu đoạn ngắn
        tts = gTTS(text=clean_text, lang='vi', slow=False)
        tts.save(output_path)
        return output_path
    else:
        raise ValueError("Chưa hỗ trợ nguồn giọng đọc này")

async def generate_single_tts(segment, output_folder, voice_source, voice_param, api_key):
    import shared_state
    if shared_state.stop_requested:
        raise Exception("Bị hủy bởi lệnh /stop")
    import re
    text = segment.content.strip()
    if not text or not re.search(r'\w', text):
        return None
        
    audio_filename = f"{segment.index}.mp3"
    audio_path = os.path.join(output_folder, audio_filename)
    
    for attempt in range(5):
        try:
            if voice_source == "fpt":
                try:
                    await generate_tts_fpt(text, audio_path, api_key, voice="banmai")
                except FPTQuotaError as q_err:
                    print(f"CẢNH BÁO FPT: {q_err}. Fallback vĩnh viễn sang Edge TTS (Hoài My)")
                    voice_source = "edge"
                    await generate_tts_edge(text, audio_path, voice_param)
            
            if voice_source == "edge":
                if voice_param == "vi-VN-HoaiMyNeural":
                    # Giảm pitch xuống +15Hz theo ý người dùng (-30Hz so với trước đó)
                    await generate_tts_edge(text, audio_path, voice_param, pitch="+15Hz", rate="+15%")
                    audio = AudioSegment.from_file(audio_path)
                    duration_s = len(audio) / 1000.0
                    expected_s = (segment.end - segment.start).total_seconds()
                    
                    if expected_s > 0 and duration_s > expected_s:
                        ratio = duration_s / expected_s
                        ratio = min(ratio, 1.8) # Đẩy tốc độ tối đa 1.8x
                        temp_speed = audio_path.replace(".mp3", "_speed.mp3")
                        import subprocess, shutil
                        subprocess.run(["ffmpeg", "-y", "-i", audio_path, "-filter:a", f"atempo={ratio:.2f}", temp_speed], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0)
                        if os.path.exists(temp_speed):
                            shutil.move(temp_speed, audio_path)
                        
                    import subprocess, shutil
                    temp_filtered = audio_path.replace(".mp3", "_filtered.mp3")
                    # Bộ lọc tối ưu: Cắt bớt dải trầm (bass) để giọng thanh hơn, giữ nguyên dải treble để trong trẻo
                    # 1. highpass=f=100 (cắt bỏ phần trầm đục)
                    # 2. eq +3dB ở 3500Hz & treble +3dB (tăng độ sáng, sắc nét rõ chữ)
                    # 3. acompressor (cân bằng âm lượng mượt mà)
                    clear_filter = "highpass=f=100,equalizer=f=3500:width_type=q:width=1.5:g=3,treble=g=3,acompressor=threshold=-15dB:ratio=3:attack=5:release=50:makeup=5dB"
                    subprocess.run(["ffmpeg", "-y", "-i", audio_path, "-filter:a", clear_filter, temp_filtered], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0)
                    if os.path.exists(temp_filtered):
                        shutil.move(temp_filtered, audio_path)
                else:
                    await generate_tts_edge(text, audio_path, voice_param, pitch="+0Hz", rate="+5%")
                    audio = AudioSegment.from_file(audio_path)
                    duration_s = len(audio) / 1000.0
                    expected_s = (segment.end - segment.start).total_seconds()
                    if duration_s > expected_s + 0.3:
                        ratio = duration_s / expected_s
                        rate_percent = int((ratio - 1.0) * 100)
                        rate_percent = min(rate_percent, 100)
                        rate_str = f"+{rate_percent}%"
                        await generate_tts_edge(text, audio_path, voice_param, pitch="+0Hz", rate=rate_str)
                    
                    import subprocess, shutil
                    temp_filtered = audio_path.replace(".mp3", "_filtered.mp3")
                    clear_filter = "highpass=f=80,equalizer=f=150:width_type=q:width=1.5:g=3,equalizer=f=3500:width_type=q:width=1.5:g=3,treble=g=3,acompressor=threshold=-15dB:ratio=3:attack=5:release=50:makeup=5dB"
                    subprocess.run(["ffmpeg", "-y", "-i", audio_path, "-filter:a", clear_filter, temp_filtered], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0)
                    if os.path.exists(temp_filtered):
                        shutil.move(temp_filtered, audio_path)
            elif voice_source in ["elevenlabs", "viettel"]:
                await generate_tts_external(text, audio_path, source=voice_source, api_key=api_key)
            elif voice_source == "rvc":
                temp_edge_raw = audio_path.replace(".mp3", "_temp_raw.mp3")
                temp_edge_rvc = audio_path.replace(".mp3", "_temp_rvc.mp3")
                
                # Base TTS: Dùng Hoài My gốc (không bóp pitch) để giữ vẹn nguyên khả năng đọc trôi chảy, ngắt nghỉ xuất sắc của cô ấy.
                # Sự "trộn lẫn" sẽ được thực hiện ở bộ lọc RVC.
                await generate_tts_edge(text, temp_edge_raw, "vi-VN-HoaiMyNeural", pitch="+0Hz", rate="+0%")
                
                # 1. CLONE RVC TRƯỚC (Trên audio tốc độ gốc để thuật toán bắt chính xác 100% phụ âm)
                await apply_rvc_clone(temp_edge_raw, temp_edge_rvc, voice_param)
                
                # 2. ÉP TỐC ĐỘ SAU (Giúp giữ nguyên vẹn độ rõ nét của RVC)
                audio = AudioSegment.from_file(temp_edge_rvc)
                duration_s = len(audio) / 1000.0
                expected_s = (segment.end - segment.start).total_seconds()
                
                if expected_s > 0 and duration_s > expected_s + 0.3:
                    ratio = duration_s / expected_s
                    ratio = min(ratio, 2.0)
                    import subprocess
                    subprocess.run(["ffmpeg", "-y", "-i", temp_edge_rvc, "-filter:a", f"atempo={ratio}", audio_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0)
                else:
                    import shutil
                    shutil.copy(temp_edge_rvc, audio_path)
                
                # Xóa file tạm
                try:
                    os.remove(temp_edge_raw)
                    os.remove(temp_edge_rvc)
                except:
                    pass
            
            # Lấy thời lượng thực tế của file audio cuối cùng
            final_audio = AudioSegment.from_file(audio_path)
            actual_duration_s = len(final_audio) / 1000.0
            
            return {
                "index": segment.index,
                "path": audio_path,
                "start": segment.start.total_seconds(),
                "end": segment.end.total_seconds(),
                "actual_audio_duration": actual_duration_s,
                "content": text
            }
        except Exception as e:
            print(f"Lỗi TTS đoạn {segment.index} (Lần {attempt+1}): {e}")
            await asyncio.sleep(1.5)
            
    print(f"Bỏ qua đoạn {segment.index} vì lỗi mạng liên tục.")
    return None

async def generate_dubbing_audio(translated_segments, output_folder, voice_source="edge", voice_param="vi-VN-HoaiMyNeural", api_key=""):
    print(f"Generating TTS for dubbing using {voice_source} (Parallel)...")
    os.makedirs(output_folder, exist_ok=True)
    
    tasks = [
        generate_single_tts(seg, output_folder, voice_source, voice_param, api_key)
        for seg in translated_segments
    ]
    
    results = await asyncio.gather(*tasks)
    
    # Lọc bỏ các kết quả None và sắp xếp lại theo thứ tự (dù gather đã trả về đúng thứ tự, nhưng chắc chắn hơn)
    audio_files = [res for res in results if res is not None]
    return audio_files
