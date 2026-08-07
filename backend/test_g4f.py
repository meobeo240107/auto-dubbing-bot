import sys
import g4f

def test_g4f():
    try:
        print("Testing g4f...")
        response = g4f.ChatCompletion.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": "Dịch cụm từ '退膜神器' sang tiếng Việt. Trả về đúng 1 từ/cụm từ, không giải thích."}]
        )
        print("G4F Success:", response)
    except Exception as e:
        print("G4F Error:", e)

if __name__ == "__main__":
    test_g4f()
