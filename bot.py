import requests
import time
import threading
import os
from flask import Flask

# ================= تنظیمات =================
BOT_TOKEN = "CIIGEF0QIJHVUSDQGHPOIFIMVNHCLZIQWOUQNYKYQUZQRCSQASUOKWUTOMRMKRMR"
API_URL = "https://afrabar.ir/barname/api_save_barnameh.php" 
SECRET_TOKEN = "MY_SUPER_SECRET_TOKEN_123"
RUBIKA_API = f"https://botapi.rubika.ir/v3/bot{BOT_TOKEN}"

# ================= وب‌سرور برای Koyeb =================
app = Flask(__name__)

@app.route('/')
def health():
    return "Bot is running!"

# ================= منطق ربات =================
user_states = {}
user_data = {}

STEPS = [
    ("template", "سلام! لطفاً نوع فرم بارنامه را انتخاب کنید:\n1. فرم تبریز\n2. فرم تهران\n(عدد 1 یا 2 را ارسال کنید)"),
    ("origin", "مبدأ بارگیری (شهر) را وارد کنید:"),
    ("destination", "مقصد تخلیه (شهر) را وارد کنید:"),
    ("sender_name", "نام فرستنده را وارد کنید:"),
    ("sender_phone", "تلفن فرستنده را وارد کنید:"),
    ("receiver_name", "نام گیرنده را وارد کنید:"),
    ("receiver_phone", "تلفن گیرنده را وارد کنید:"),
    ("driver_name", "نام راننده را وارد کنید:"),
    ("plate", "شماره پلاک را وارد کنید (مثال: 12 ب 345 ایران 67):"),
    ("cargo_name", "نام محموله را وارد کنید:"),
    ("cargo_value", "ارزش کالا (به ریال) را وارد کنید. (اگر بیمه نمی‌خواهید، 0 وارد کنید):"),
    ("weight_kg", "وزن محموله (کیلوگرم) را وارد کنید:")
]

def send_message(chat_id, text):
    url = f"{RUBIKA_API}/sendMessage"
    try: requests.post(url, json={"chat_id": chat_id, "text": text}, timeout=10)
    except Exception as e: print(f"Error: {e}")

def parse_plate(plate_str):
    parts = plate_str.split()
    if len(parts) >= 5: return parts[0], parts[1], parts[2], parts[4]
    return "", "", "", ""

def bot_loop():
    last_update_id = 0
    print("Bot Started...")
    while True:
        try:
            url = f"{RUBIKA_API}/getUpdates?offset={last_update_id + 1}"
            response = requests.get(url, timeout=10).json()
            if response.get('result') and isinstance(response['result'], list):
                for update in response['result']:
                    last_update_id = update['update_id']
                    if 'message' not in update or 'text' not in update['message']: continue
                    chat_id = update['message']['chat_id']
                    text = update['message']['text'].strip()
                    
                    if chat_id not in user_states:
                        user_states[chat_id] = 0
                        user_data[chat_id] = {}
                    
                    current_step = user_states[chat_id]
                    if current_step >= len(STEPS): continue
                    
                    step_key, _ = STEPS[current_step]
                    
                    if step_key == "template":
                        if text == "1": user_data[chat_id]['background_type'] = 'tabriz'
                        elif text == "2": user_data[chat_id]['background_type'] = 'tehran'
                        else:
                            send_message(chat_id, "لطفاً فقط عدد 1 یا 2 را وارد کنید.")
                            continue
                    elif step_key == "plate":
                        p1, pl, p2, p3 = parse_plate(text)
                        if not p1:
                            send_message(chat_id, "فرمت پلاک اشتباه است. دوباره وارد کنید.")
                            continue
                        user_data[chat_id]['plate_part1'] = p1
                        user_data[chat_id]['plate_letter'] = pl
                        user_data[chat_id]['plate_part2'] = p2
                        user_data[chat_id]['plate_part3'] = p3
                    else:
                        user_data[chat_id][step_key] = text
                    
                    user_states[chat_id] += 1
                    
                    if user_states[chat_id] >= len(STEPS):
                        send_message(chat_id, "در حال صدور بارنامه...")
                        payload = user_data[chat_id].copy()
                        payload['token'] = SECRET_TOKEN
                        try:
                            api_res = requests.post(API_URL, json=payload, timeout=15).json()
                            if api_res.get('ok'):
                                send_message(chat_id, f"✅ بارنامه صادر شد!\nشماره: {api_res['number']}\nلینک: {api_res['link']}")
                            else: send_message(chat_id, f"❌ خطا: {api_res.get('msg')}")
                        except Exception as e: send_message(chat_id, "❌ خطای شبکه.")
                        del user_states[chat_id]; del user_data[chat_id]
                    else:
                        send_message(chat_id, STEPS[user_states[chat_id]][1])
        except Exception as e: print(f"Loop Error: {e}")
        time.sleep(2)

# ================= اجرای همزمان =================
if __name__ == "__main__":
    bot_thread = threading.Thread(target=bot_loop)
    bot_thread.daemon = True
    bot_thread.start()
    
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
