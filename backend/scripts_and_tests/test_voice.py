import asyncio
from edge_tts import Communicate
from pydub import AudioSegment
import os
import sys

sys.path.append(os.path.abspath("."))
import ai_utils

async def test():
    text = "Xin chào các bạn. Mình là một cô gái đến từ Hà Nội. Chúc các bạn một ngày tốt lành!"
    raw_path = "test_namminh.mp3"
    out_path = "test_chimai_northern.mp3"
    
    # 1. Sinh giọng nam miền Bắc
    comm = Communicate(text, "vi-VN-NamMinhNeural")
    await comm.save(raw_path)
    print("Created base Nam Minh TTS.")
    
    # 2. RVC Clone
    import shared_state
    model_path = os.path.abspath(os.path.join("..", "workspace", "models", "rvc", "ChiMai.pth"))
    
    # Configure RVC for Male -> Female conversion
    if ai_utils.global_rvc_instance is None:
        from rvc_python.infer import RVCInference
        ai_utils.global_rvc_instance = RVCInference(device="cuda:0")
        ai_utils.global_rvc_instance.load_model(model_path)
    
    # +12 semitones to shift male to female pitch
    ai_utils.global_rvc_instance.set_params(
        f0up_key=12,
        f0method="rmvpe",
        index_rate=0.75,
        protect=0.20,
        filter_radius=7,
        rms_mix_rate=0.1
    )
    ai_utils.global_rvc_instance.infer_file(raw_path, out_path)
    print("Done RVC.")

if __name__ == "__main__":
    asyncio.run(test())
