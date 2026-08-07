import sys
try:
    with open('telegram_bot.py', 'rb') as f:
        raw = f.read()
    if raw.startswith(b'\xef\xbb\xbf'):
        raw = raw[3:]
    text = raw.decode('utf-8')
    original_bytes = text.encode('cp1252')
    original_text = original_bytes.decode('utf-8')
    with open('telegram_bot.py', 'wb') as f:
        f.write(original_text.encode('utf-8'))
    print('Encoding fixed successfully!')
except Exception as e:
    print('Error:', e)
