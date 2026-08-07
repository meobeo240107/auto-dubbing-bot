import requests
import base64
import os

def test_tiktok_tts(text, voice, output_file):
    # Endpoint from oscie57/tiktok-voice and others
    url = "https://api16-normal-v6.tiktokv.com/media/api/text/speech/invoke/"
    headers = {
        "User-Agent": "com.zhiliaoapp.musically/2022600030 (Linux; U; Android 7.1.2; en_US; SM-G988N; Build/NRD90M;tt-ok/3.12.13.1)",
        "Cookie": "sessionid=123" # Sometimes needs a random sessionid
    }
    params = {
        "text_speaker": voice,
        "req_text": text,
        "speaker_map_type": 0,
        "aid": 1233
    }
    
    try:
        response = requests.post(url, headers=headers, params=params)
        data = response.json()
        
        if data.get("message") == "Success":
            vstr = data["data"]["v_str"]
            audio_bytes = base64.b64decode(vstr)
            with open(output_file, "wb") as f:
                f.write(audio_bytes)
            print(f"Success! Saved to {output_file}")
            return True
        else:
            print("Failed:", data)
            return False
    except Exception as e:
        print("Error:", e)
        return False

if __name__ == "__main__":
    test_tiktok_tts("Hello, this is a test.", "en_us_001", "test_tiktok.mp3")
