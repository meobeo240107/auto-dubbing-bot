import os
import subprocess
import sys

# Windows flag to hide terminal windows
CREATE_NO_WINDOW = 0x08000000 if sys.platform == 'win32' else 0
import ffmpeg

def extract_audio_from_video(video_path, output_audio_path):
    """
    Trích xuất âm thanh từ video dưới dạng file .wav chất lượng cao (44.1kHz, Stereo)
    để vừa dùng cho Whisper (tự downsample), vừa dùng cho Demucs để nhạc nền trong vắt.
    """
    print(f"Extracting high-quality audio from {video_path}...")
    try:
        cmd = (
            ffmpeg
            .input(video_path)
            .output(output_audio_path, acodec='pcm_s16le', ac=2, ar='44100')
            .overwrite_output()
            .compile()
        )
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=CREATE_NO_WINDOW)
        return True
    except ffmpeg.Error as e:
        print("FFmpeg extract audio error:", e)
        return False

def separate_vocals_demucs(input_audio_path, output_dir):
    """
    Sử dụng Demucs để tách vocal ra khỏi nhạc nền.
    Trả về (vocals_path, no_vocals_path)
    """
    import subprocess
    import sys
    import os
    
    # Resolve đường dẫn tuyệt đối để tránh lỗi ký tự đặc biệt và ".."
    input_audio_path = os.path.abspath(input_audio_path)
    output_dir = os.path.abspath(output_dir)
    
    if not os.path.exists(input_audio_path):
        print(f"File audio không tồn tại: {input_audio_path}")
        return input_audio_path, input_audio_path
    
    print(f"Bắt đầu tách âm thanh bằng Demucs cho {input_audio_path}...")
    try:
        # Dùng python của venv để đảm bảo demucs được tìm thấy
        venv_python = os.path.join(os.path.dirname(os.path.abspath(__file__)), "venv", "Scripts", "python.exe")
        if not os.path.exists(venv_python):
            venv_python = sys.executable  # Fallback
        
        cmd = [
            venv_python, "-m", "demucs",
            input_audio_path,
            "-n", "htdemucs_ft",
            "--two-stems", "vocals",
            "-j", "1",
            "-o", output_dir
        ]
        subprocess.run(cmd, check=True, timeout=600, creationflags=CREATE_NO_WINDOW)
        
        base_name = os.path.splitext(os.path.basename(input_audio_path))[0]
        demucs_out_dir = os.path.join(output_dir, "htdemucs_ft", base_name)
        
        vocals_path = os.path.join(demucs_out_dir, "vocals.wav")
        no_vocals_path = os.path.join(demucs_out_dir, "no_vocals.wav")
        
        if os.path.exists(vocals_path) and os.path.exists(no_vocals_path):
            print(f"Demucs tách thành công! Vocals: {vocals_path}")
            return vocals_path, no_vocals_path
        else:
            print(f"Demucs chạy xong nhưng không tìm thấy file output tại {demucs_out_dir}")
            # Liệt kê các file có trong thư mục output để debug
            if os.path.exists(demucs_out_dir):
                print(f"Nội dung thư mục: {os.listdir(demucs_out_dir)}")
            return input_audio_path, input_audio_path # Fallback
            
    except Exception as e:
        print(f"Lỗi khi chạy Demucs: {e}")
        return input_audio_path, input_audio_path # Fallback

def merge_audio_files_with_delay(video_path, original_audio_path, dubbing_audio_files, output_video_path, original_volume=0.1, dub_volume=1.0):
    """
    Ghép các file âm thanh lồng tiếng lại theo đúng mốc thời gian, trộn với âm thanh gốc đã giảm âm lượng,
    sau đó ghép vào video đã được làm mờ/chèn sub (đầu vào là video câm hoặc video gốc tuỳ cấu hình).
    """
    # Create a complex filter for ffmpeg to mix all audio
    # This is a basic implementation. A more robust way is using PyDub to generate a single mixed audio track first.
    pass
    
def mix_audio_pydub(original_audio_path, dubbing_audio_files, output_mixed_audio_path, original_volume_db=-5, dubbing_volume_db=1):
    """
    Trộn âm thanh bằng PyDub. Giảm âm lượng nhạc nền (-15dB, tức khoảng 15-20%) và chèn giọng đọc AI vào đúng vị trí.
    """
    print("Mixing audio tracks using pydub...")
    try:
        import subprocess
        # Ngăn pydub nháy màn hình đen ffmpeg liên tục trên Windows
        original_popen = subprocess.Popen
        class PopenNoWindow(original_popen):
            def __init__(self, *args, **kwargs):
                if hasattr(subprocess, 'CREATE_NO_WINDOW'):
                    kwargs['creationflags'] = kwargs.get('creationflags', 0) | subprocess.CREATE_NO_WINDOW
                super().__init__(*args, **kwargs)
        subprocess.Popen = PopenNoWindow
        
        from pydub import AudioSegment
        
        # Load audio gốc và giảm âm lượng
        mixed = AudioSegment.from_file(original_audio_path)
        mixed = mixed + original_volume_db
        
        # Chèn từng file lồng tiếng (Khớp chính xác 100% thời gian với Subtitle)
        for dub in dubbing_audio_files:
            if not os.path.exists(dub["path"]):
                continue
            dub_audio = AudioSegment.from_file(dub["path"])
            # Tăng âm lượng giọng đọc nếu cần
            dub_audio = dub_audio + dubbing_volume_db
            
            position_ms = int(dub["start"] * 1000)
            mixed = mixed.overlay(dub_audio, position=position_ms)
            
        mixed.export(output_mixed_audio_path, format="wav")
        return output_mixed_audio_path
    except Exception as e:
        print(f"PyDub error: {e}. Fallback to original audio.")
        import shutil
        shutil.copy(original_audio_path, output_mixed_audio_path)
        return output_mixed_audio_path

def process_video(video_path, srt_path, mixed_audio_path, output_video_path, font_name="Arial", font_color="&H00FFFFFF", font_weight=1, main_y_pct=0.75):
    """
    Dùng ffmpeg để chèn hardsub và ghép âm thanh mới. Bỏ tính năng làm mờ.
    """
    print("Processing final video with styled subtitles and NVENC...")
    srt_escaped = srt_path.replace('\\', '/').replace(':', '\\:')
    
    bold_val = -1 if font_weight > 1 else 0
    style_str = f"FontName={font_name},FontSize=14,PrimaryColour={font_color},Bold={bold_val},Outline=2,Shadow=1,MarginV=40,BorderStyle=1"
        
    try:
        # Tự động tính toán Bitrate để đảm bảo file LUÔN DƯỚI 50MB (Giới hạn của Telegram)
        video_duration = 0
        try:
            probe = ffmpeg.probe(video_path)
            video_duration = float(probe['format']['duration'])
        except Exception:
            video_duration = 180 # Fallback 3 phút
            
        target_size_mb = 48.0 # Trừ hao 2MB cho headers và audio
        target_size_kbits = target_size_mb * 8192
        audio_bitrate_kbps = 128
        audio_size_kbits = audio_bitrate_kbps * video_duration
        
        video_bitrate_kbps = (target_size_kbits - audio_size_kbits) / video_duration if video_duration > 0 else 2000
        # Theo yêu cầu của người dùng, ÉP BẮT BUỘC CHẤT LƯỢNG CAO (>720p). 
        # Độ nét 720p đòi hỏi tối thiểu 1500kbps. Nếu vượt quá 50MB, bot sẽ cắt nhỏ video ra ở khâu gửi.
        video_bitrate_kbps = max(1500, min(3000, int(video_bitrate_kbps)))
        
        b_v = f"{video_bitrate_kbps}k"
        maxrate = f"{int(video_bitrate_kbps * 1.5)}k"
        bufsize = f"{int(video_bitrate_kbps * 2)}k"
        
        if srt_path.endswith('.ass'):
            filter_complex = f"subtitles='{srt_escaped}'"
        else:
            filter_complex = f"subtitles='{srt_escaped}':force_style='{style_str}'"
        
        cmd = [
            'ffmpeg',
            '-y',
            '-i', video_path,
            '-i', mixed_audio_path,
            '-vf', filter_complex,
            '-map', '0:v',
            '-map', '1:a',
            '-c:v', 'h264_nvenc', # Sử dụng CUDA/NVENC
            '-preset', 'fast',    # NVENC preset
            '-pix_fmt', 'yuv420p', # BẮT BUỘC: Ép định dạng pixel để hỗ trợ giải mã phần cứng trên iOS/Android (chống lag/giật)
            '-b:v', b_v,          # Bitrate tính toán tự động ép nén
            '-maxrate', maxrate,
            '-bufsize', bufsize,
            '-c:a', 'aac',
            '-b:a', '192k',       # Tăng bitrate audio lên 192kbps để nhạc nền + giọng nói trong trẻo hơn
            '-movflags', '+faststart', # BẮT BUỘC: Di chuyển index video lên đầu file để Telegram có thể stream ngay lập tức mà không cần tải hết file
            '-shortest',
            output_video_path
        ]
        
        subprocess.run(cmd, check=True, creationflags=CREATE_NO_WINDOW)
        return True
    except subprocess.CalledProcessError as e:
        print("FFmpeg process video error:", e)
        return False
