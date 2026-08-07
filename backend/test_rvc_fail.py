import asyncio
from ai_utils import generate_single_tts

async def main():
    print("Testing generate_single_tts...")
    voice_param = "fpt_banmai"
    texts = [
        "Xin chào",
        "Tuyệt vời",
        "Có",
        "Đoạn này rất ngắn",
        "Một hai ba bốn năm sáu bảy tám chín mười"
    ]
    tasks = []
    for i, text in enumerate(texts):
        tasks.append(generate_single_tts(i, text, "rvc", 0, voice_param))
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    for i, res in enumerate(results):
        if isinstance(res, Exception):
            print(f"Segment {i} FAILED: {res}")
        elif res is None:
            print(f"Segment {i} RETURNED NONE")
        else:
            print(f"Segment {i} SUCCESS: {res}")

if __name__ == "__main__":
    asyncio.run(main())
