import telebot
from telebot import types
import os
import threading
import subprocess
import requests

# بيانات البوت والقناة
API_TOKEN = '8211772439:AAERwOdOwLqbu37hMvmkNPJCATByrcoFc7U'
CHANNEL_ID = '@midosaadoffichall' 
CHANNEL_LINK = "https://t.me/midosaadoffichall"
ADMIN_ID = 8574641551 
WEB_APP_URL = "https://drmazer.github.io"

bot = telebot.TeleBot(API_TOKEN)
user_list = set()

# --- وظيفة تشغيل البروكسي ---
def run_proxy():
    port = os.environ.get("PORT", "8080")
    print(f"🚀 Starting SOCKS5 Proxy on port {port}...")
    # تشغيل البروكسي (بدون يوزر وباسورد حالياً للتجربة)
    subprocess.run([
        "proxy", "--hostname", "0.0.0.0", "--port", port,
        "--plugins", "proxy.plugin.SocksProtocolHandler"
    ])

# --- وظائف البوت ---
def check_sub(user_id):
    try:
        status = bot.get_chat_member(CHANNEL_ID, user_id).status
        return status in ['member', 'administrator', 'creator']
    except:
        return False

def notify_admin(text):
    try:
        bot.send_message(ADMIN_ID, text)
    except:
        pass

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    user_list.add(user_id)
    
    # جلب الـ IP بتاع السيرفر لإظهاره للأدمن فقط للتأكد
    server_ip = requests.get('https://api.ipify.org').text
    
    first_name = message.from_user.first_name
    welcome_text = (
        f"🟠 **أهلاً بك يا {first_name}**\n"
        "🔸 هذا البوت مخصص لخدمات البروكسي السريعة.\n"
        "🔸 يرجى الاشتراك في القناة أولاً لتفعيل البوت."
    )

    markup = types.InlineKeyboardMarkup()
    btn_sub = types.InlineKeyboardButton("📢 اشترك", url=CHANNEL_LINK)
    btn_check = types.InlineKeyboardButton("✅ تحقق", callback_data="verify")
    markup.add(btn_sub, btn_check)
    
    bot.send_message(message.chat.id, welcome_text, reply_markup=markup, parse_mode="Markdown")
    if user_id == ADMIN_ID:
        bot.send_message(ADMIN_ID, f"🚀 سيرفرك شغال بـ IP أمريكي:\n`{server_ip}`", parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    if call.data == "verify":
        if check_sub(call.from_user.id):
            show_main_menu(call.message)
        else:
            bot.answer_callback_query(call.id, "❌ اشترك في القناة أولاً!", show_alert=True)

def show_main_menu(message):
    markup = types.InlineKeyboardMarkup()
    web_app = types.WebAppInfo(WEB_APP_URL)
    btn_site = types.InlineKeyboardButton("🚀 فتح موقع البروكسي", web_app=web_app)
    markup.add(btn_site)
    bot.send_message(message.chat.id, "🔥 اضغط لفتح الموقع:", reply_markup=markup)

@bot.message_handler(commands=['broadcast'])
def broadcast_request(message):
    if message.from_user.id == ADMIN_ID:
        msg = bot.reply_to(message, "🟠 ارسل النص للإذاعة:")
        bot.register_next_step_handler(msg, start_broadcasting)

def start_broadcasting(message):
    for user_id in list(user_list):
        try: bot.send_message(user_id, message.text)
        except: continue
    bot.send_message(ADMIN_ID, "✅ تمت الإذاعة!")

# --- التشغيل المزدوج ---
if __name__ == "__main__":
    # 1. تشغيل البروكسي في خيط منفصل (Background)
    proxy_thread = threading.Thread(target=run_proxy)
    proxy_thread.start()
    
    # 2. تشغيل البوت
    print("🚀 البوت والبروكسي قيد التشغيل...")
    bot.infinity_polling()
