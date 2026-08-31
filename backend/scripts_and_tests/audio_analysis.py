import parselmouth
import numpy as np
import traceback

def detect_gender(audio_path):
    """
    Sử dụng thư viện parselmouth (Praat) để phân tích tần số cơ bản (F0).
    Trả về 'female' hoặc 'male' dựa trên median pitch.
    """
    try:
        snd = parselmouth.Sound(audio_path)
        pitch = snd.to_pitch()
        pitch_values = pitch.selected_array['frequency']
        
        # Lọc bỏ các khung âm thanh không chứa giọng nói (0 Hz)
        voiced_pitches = pitch_values[pitch_values > 0]
        
        if len(voiced_pitches) == 0:
            print("Không tìm thấy âm thanh có cao độ rõ ràng, mặc định chọn giọng Nữ.")
            return "female" 
        
        median_pitch = np.median(voiced_pitches)
        print(f"📊 Đã phân tích F0 (Median Pitch): {median_pitch:.2f} Hz")
        
        # 165Hz là mốc chia chuẩn để phân biệt Nam/Nữ
        if median_pitch > 165:
            print("=> Giọng Nữ (Female)")
            return "female"
        else:
            print("=> Giọng Nam (Male)")
            return "male"
            
    except Exception as e:
        print(f"Lỗi khi detect_gender: {e}")
        traceback.print_exc()
        return "female"  # Fallback mặc định là Hoài My
