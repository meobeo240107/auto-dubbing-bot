import sys
try:
    with open('telegram_bot.py', 'rb') as f:
        raw = f.read()
    # Reverse the PowerShell encoding corruption (it read UTF-8 as cp1252 and saved as UTF-8)
    text = raw.decode('utf-8')
    original_bytes = text.encode('cp1252')
    original_text = original_bytes.decode('utf-8')
    with open('telegram_bot.py', 'wb') as f:
        f.write(original_text.encode('utf-8'))
    print('Encoding fixed successfully!')
except Exception as e:
    print('Error:', e)
