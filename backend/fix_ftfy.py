import ftfy
with open('telegram_bot.py', 'r', encoding='utf-8') as f:
    text = f.read()
fixed_text = ftfy.fix_text(text)
with open('telegram_bot.py', 'w', encoding='utf-8') as f:
    f.write(fixed_text)
print('Fixed mojibake successfully!')
