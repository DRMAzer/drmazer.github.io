import threading
import time
import telebot
from telebot import types
import datetime
import json
import requests
import base64
import random

# --- البيانات الأساسية (تم تصحيح التنسيق) ---
API_TOKEN = '8211772439:AAFMF52bVxMIJTmqq88BTHkq-hbhKS5JfxQ'
ADMIN_ID = 8574641551 
CHANNEL_ID = '@midosaadoffichall' 
CHANNEL_LINK = "https://t.me/midosaadoffichall"

# بيانات جيت هوب - تأكد أنها تبدأ من أول السطر تماماً بدون مسافات
GITHUB_TOKEN = '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'
REPO_PATH = "DRMAzer/drmazer.github.io"
REPO_NAME = "DRMAzer/drmazer.github.io" 
# المسارات الجديدة لتشمل المجلد الفرعي
DATA_FILE_PATH = 'drmazer.github.io/users_data.json'
CFG_FILE_PATH = 'drmazer.github.io/3proxy.cfg'

SHIPPING_MSG = (
    "💳 **لشحن رصيدك يرجى اختيار أحد الخدمات التالية:**\n\n"
    "⚠️ **برجاء العلم أنه تتم مراجعة الطلب خلال دقائق بحد أقصى ساعة.**\n"
    f"📸 **برجاء إرسال صورة الدفع للأدمن: [اضغط هنا لمراسلة الإدارة](tg://user?id={ADMIN_ID})**"
)

PORT_DETAILS = {
    "53940": {"loc": "USA/TEXAS", "rotation": 30, "host": "shuttle.proxy.rlwy.net"},

}

# تشغيل البوت
bot = telebot.TeleBot(API_TOKEN)

# متغيرات الرام
user_balances = {}
user_list = set()
active_proxies = {}

# --- نظام إدارة GitHub ---
def github_manager(file_path, new_content=None, mode="read"):
    url = f"https://api.github.com/repos/{REPO_NAME}/contents/{file_path}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    try:
        res = requests.get(url, headers=headers).json()
        if mode == "read":
            content = base64.b64decode(res['content']).decode('utf-8')
            return json.loads(content)
        sha = res['sha']
        updated_b64 = base64.b64encode(new_content.encode('utf-8')).decode('utf-8')
        payload = {"message": "Update Data", "content": updated_b64, "sha": sha}
        put_res = requests.put(url, headers=headers, json=payload)
        return put_res.status_code in [200, 201]
    except: 
        return None if mode == "read" else False

def load_data():
    global user_balances, user_list, active_proxies
    print("🔄 محاولة الاتصال بجيت هوب لسحب البيانات...")
    data = github_manager(DATA_FILE_PATH, mode="read")
    
    if data is not None:
        user_balances = data.get("balances", {})
        user_list = set(data.get("users", []))
        active_proxies = data.get("active_proxies", {})
        print(f"✅ تم بنجاح سحب بيانات {len(user_list)} مستخدم.")
    else:
        print("❌ فشل ذريع في السحب! البوت سيتوقف لحماية بياناتك.")
        exit()

def save_data():
    # 1. حفظ بيانات JSON أولاً (لضمان عدم ضياع الأرصدة)
    try:
        data_json = {
            "balances": user_balances, 
            "users": list(user_list), 
            "active_proxies": active_proxies
        }
        github_manager(DATA_FILE_PATH, json.dumps(data_json, indent=4), mode="write")
    except Exception as e:
        print(f"❌ خطأ في حفظ بيانات JSON: {e}")

    # 2. إعداد ملف 3proxy.cfg ليتناسب مع بورت Railway
    cfg_content = (
        "daemon\n"
        "maxconn 1000\n"
        "nscache 65536\n"
        "timeouts 1 5 30 60 180 1800 15 60\n"
        "setgid 65535\n"
        "setuid 65535\n"
        "stacksize 62768\n"
        "flush\n"
        "auth strong\n\n"
    )

    # إضافة يوزرات المستخدمين
    for uid, proxies in active_proxies.items():
        for proxy in proxies:
            cfg_content += f"users {proxy['user']}:CL:{proxy['pass']}\n"
            cfg_content += f"allow {proxy['user']}\n"

    # التعديل الجوهري للربط بسيرفر Railway
    # يتم توجيه البيانات من باقة AT&T (95.169.180.49:8496) إلى بورت Railway الداخلي (8080)
    cfg_content += "\n# الربط بالوكيل الأم (Parent Proxy)\n"
    cfg_content += "parent 1000 socks5 95.169.180.49 8496\n"
    cfg_content += "proxy -p8080 -a -n\n"
    cfg_content += "socks -p8080 -a -n\n"

    # كود رفع الملف إلى GitHub
    try:
        url = f"https://api.github.com/repos/{REPO_PATH}/contents/{CFG_FILE_PATH}"
        res = requests.get(url, headers={"Authorization": f"token {GITHUB_TOKEN}"})
        sha = res.json().get('sha') if res.status_code == 200 else None
        
        payload = {
            "message": "Update proxy config for Railway",
            "content": base64.b64encode(cfg_content.encode()).decode(),
            "sha": sha
        }
        put_res = requests.put(url, json=payload, headers={"Authorization": f"token {GITHUB_TOKEN}"})
        if put_res.status_code in [200, 201]:
            print(f"✅ تم تحديث السيرفر بنجاح. بورت العميل: 53940")
    except Exception as e:
        print(f"❌ خطأ في تحديث GitHub: {e}")


def auto_clean_expired():
    global active_proxies
    while True:
        try:
            now = datetime.datetime.now()
            changed = False
            for uid in list(active_proxies.keys()):
                updated_subs = []
                for sub in active_proxies[uid]:
                    expiry_dt = datetime.datetime.strptime(sub['expiry'], "%Y-%m-%d %H:%M:%S")
                    remaining_seconds = (expiry_dt - now).total_seconds()
                    
                    # تنبيه قبل ساعة من الانتهاء
                    if 0 < remaining_seconds <= 3600 and not sub.get('warned_1h'):
                        warn_msg = (f"⚠️ **تنبيه انتهاء الباقة**\n\nمتبقي ساعة واحدة على انتهاء البروكسي: `{sub['user']}`")
                        markup = types.InlineKeyboardMarkup(row_width=1)
                        markup.add(
                            types.InlineKeyboardButton("🔄 يوم - 0.50$", callback_data=f"renew_1d_{sub['user']}"),
                            types.InlineKeyboardButton("🔄 12 ساعة - 0.35$", callback_data=f"renew_12h_{sub['user']}"),
                            types.InlineKeyboardButton("🔄 ساعتين - 0.20$", callback_data=f"renew_2h_{sub['user']}"), # إضافة الساعتين
                            types.InlineKeyboardButton("🔙 العودة", callback_data="back")
                        )
                        try:
                            bot.send_message(uid, warn_msg, reply_markup=markup, parse_mode="Markdown")
                            sub['warned_1h'] = True
                            changed = True
                        except: pass
                    
                    if remaining_seconds > 0: 
                        updated_subs.append(sub)
                    else: 
                        changed = True # الباقة انتهت فعلياً
                
                active_proxies[uid] = updated_subs
                if not active_proxies[uid]: 
                    del active_proxies[uid]
            
            if changed: 
                save_data()
        except Exception as e:
            print(f"Error in auto_clean: {e}")
        time.sleep(60)


# --- القائمة الرئيسية ---
def main_menu(chat_id, user_id):
    bal = user_balances.get(str(user_id), 0.0)
    markup = types.InlineKeyboardMarkup(row_width=2)
    # --- التعديل هنا ---
    markup.add(
        types.InlineKeyboardButton("👤 حسابي", callback_data="my_info"),
        types.InlineKeyboardButton("🌐 بروكسياتي", callback_data="my_proxies"),
        types.InlineKeyboardButton("🛒 شراء بروكسي", callback_data="buy_proxy")
    )
    # ------------------
    markup.add(types.InlineKeyboardButton("💰 قائمة الأسعار", callback_data="show_prices"),
               types.InlineKeyboardButton("💳 شحن رصيد", callback_data="top_up"))
    markup.add(types.InlineKeyboardButton("🌐 Language / اللغة", callback_data="set_lang"),
               types.InlineKeyboardButton("👨‍💻 الدعم الفني", url=f"tg://user?id={ADMIN_ID}"))
    if int(user_id) == ADMIN_ID:
        markup.add(types.InlineKeyboardButton("🛠 لوحة التحكم العليا", callback_data="admin_panel"))
    
    text = f"🏠 **القائمة الرئيسية لـ ProxyAzerbot**\n━━━━━━━━━━━━━━\n🆔 معرفك: `{user_id}`\n💰 رصيدك المتاح: `{bal}$`"
    bot.send_message(chat_id, text, reply_markup=markup, parse_mode="Markdown")


@bot.message_handler(commands=['start'])
def start(message):
    uid = str(message.from_user.id)
    if uid not in user_list:
        user_list.add(uid)
        save_data()
    markup = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("✅ تفعيل الحساب", callback_data="verify"))
    bot.send_message(message.chat.id, f"👋 مرحباً بك!\n🆔 معرفك: `{uid}`", reply_markup=markup, parse_mode="Markdown")

# --- ترتيب الهاندلرز المصلح (هنا التعديل الجوهري) ---

@bot.callback_query_handler(func=lambda call: call.data == "main_menu")
def back_to_start(call):
    uid = str(call.from_user.id)
    bot.delete_message(call.message.chat.id, call.message.message_id)
    main_menu(call.message.chat.id, uid)

@bot.callback_query_handler(func=lambda call: call.data.startswith("sel_p_"))
def handle_port_selection(call):
    port = call.data.split("_")[2]
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton(f"🟣 باقة 24 ساعة - 0.50$", callback_data=f"pay_{port}_24h_0.5"),
        types.InlineKeyboardButton(f"🔵 باقة 12 ساعة - 0.35$", callback_data=f"pay_{port}_12h_0.35"),
        types.InlineKeyboardButton(f"⚡ باقة 2 ساعة - 0.20$", callback_data=f"pay_{port}_2h_0.2"),
        types.InlineKeyboardButton("🔙 العودة لاختيار بورت آخر ↩️", callback_data="buy_proxy"),
        types.InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="main_menu")
    )
    bot.edit_message_text(f"⏱️ **لقد اخترت بورت: {port}**\nالآن اختر مدة الاشتراك المطلوب تفعيلها:", 
                          call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")
@bot.callback_query_handler(func=lambda call: call.data.startswith("renew_"))
def handle_renewal(call):
    uid = str(call.from_user.id)
    data = call.data.split("_")
    duration = data[1]
    target_user = data[2]
    
    prices = {"1d": 0.50, "12h": 0.35, "2h": 0.20}
    hours = {"1d": 24, "12h": 12, "2h": 2}
    
    cost = prices.get(duration)
    add_hours = hours.get(duration)
    
    # فحص الرصيد
    if user_balances.get(uid, 0.0) < cost:
        bot.answer_callback_query(call.id, "⚠️ رصيدك غير كافٍ للتجديد!", show_alert=True)
        return

    # التجديد
    if uid in active_proxies:
        for sub in active_proxies[uid]:
            if sub['user'] == target_user:
                # إضافة الوقت الجديد
                old_expiry = datetime.datetime.strptime(sub['expiry'], "%Y-%m-%d %H:%M:%S")
                new_expiry = old_expiry + datetime.timedelta(hours=add_hours)
                sub['expiry'] = new_expiry.strftime("%Y-%m-%d %H:%M:%S")
                # خصم الرصيد
                user_balances[uid] = round(user_balances.get(uid, 0.0) - cost, 2)
                save_data()
                bot.answer_callback_query(call.id, f"✅ تم تجديد البروكسي بنجاح!", show_alert=True)
                
                # تحديث الرسالة لتظهر الوقت الجديد
                # سنقوم بإنشاء كول باك كأنه ضغط على manage_ لتحديث الرسالة
                call.data = f"manage_{target_user}"
                manage_proxy(call) # هذه الدالة يجب أن تكون معرفة كـ handler أو function
                return
    
    bot.answer_callback_query(call.id, "❌ لم يتم العثور على البروكسي.", show_alert=True)
    
@bot.callback_query_handler(func=lambda call: call.data.startswith('renew_'))
def handle_renewal(call):
    uid = str(call.from_user.id)
    try:
        data = call.data.split('_')
        duration, target_user = data[1], data[2]
        prices = {"1d": 0.50, "12h": 0.35, "2h": 0.20}
        hours = {"1d": 24, "12h": 12, "2h": 2}
        cost, add_h = prices.get(duration), hours.get(duration)
        bal = user_balances.get(uid, 0.0)
        if bal >= cost:
            found = False
            for sub in active_proxies.get(uid, []):
                if sub['user'] == target_user:
                    old_exp = datetime.datetime.strptime(sub['expiry'], "%Y-%m-%d %H:%M:%S")
                    sub['expiry'] = (old_exp + datetime.timedelta(hours=add_h)).strftime("%Y-%m-%d %H:%M:%S")
                    sub['warned_1h'] = False
                    found = True; break
            if found:
                user_balances[uid] = round(bal - cost, 2)
                save_data()
                bot.edit_message_text(f"✅ تم التجديد! رصيدك: {user_balances[uid]}$", call.message.chat.id, call.message.message_id)
            else: bot.answer_callback_query(call.id, "❌ اليوزر غير نشط")
        else: bot.answer_callback_query(call.id, "⚠️ رصيد غير كافٍ")
    except: pass

@bot.callback_query_handler(func=lambda call: True)
def handle_query(call):
    uid = str(call.from_user.id)
    
    if call.data == "verify" or call.data == "back":
        main_menu(call.message.chat.id, uid)
    
    elif call.data == "my_info":
        bal = user_balances.get(uid, 0.0)
        bot.edit_message_text(f"👤 **معلومات حسابك:**\n━━━━━━━━━━━━━━\n🆔 معرفك: `{uid}`\n💰 رصيدك: `{bal}$`", 
                             call.message.chat.id, call.message.message_id, 
                             reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("🔙 العودة", callback_data="back")), parse_mode="Markdown")
    elif call.data == "my_proxies":
        uid = str(call.from_user.id)
        
        # فحص إذا كان للمستخدم بروكسي نشط
        if uid not in active_proxies or not active_proxies[uid]:
            bot.answer_callback_query(call.id, "❌ أنت غير مشترك في باقة بروكسي حالياً.", show_alert=True)
            return

        # عرض بروكسيات المستخدم
        markup = types.InlineKeyboardMarkup(row_width=1)
        for sub in active_proxies[uid]:
            # إنشاء زر لكل اشتراك يحتوي على اليوزر واسم البورت لتمييزه
            btn_text = f"👤 {sub['user']} | ⏳ {sub['expiry']}"
            markup.add(types.InlineKeyboardButton(btn_text, callback_data=f"manage_{sub['user']}"))
        
        markup.add(types.InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data="main_menu"))
        bot.edit_message_text("📱 **قائمة اشتراكاتك:**", call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")
        
    elif call.data.startswith("manage_"):
        uid = str(call.from_user.id)
        target_user = call.data.split("_")[1]
        
        # البحث عن تفاصيل البروكسي
        proxy_data = None
        if uid in active_proxies:
            for sub in active_proxies[uid]:
                if sub['user'] == target_user:
                    proxy_data = sub
                    break
        
        if not proxy_data:
            bot.answer_callback_query(call.id, "❌ حدث خطأ، لم يتم العثور على البروكسي.")
            return

        text = (f"⚙️ **إدارة البروكسي:** `{target_user}`\n"
                f"📅 **ينتهي في:** `{proxy_data['expiry']}`\n"
                f"🔢 **البورت الحالي:** `{proxy_data['port']}`\n\n"
                f"👇 **اختر الإجراء:**")

        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(types.InlineKeyboardButton("🔍 تفاصيل البورت الخاص بي", callback_data=f"p_details_{target_user}"))
        
        # أزرار التجديد
        markup.add(types.InlineKeyboardButton("🔄 تجديد يوم - 0.50$", callback_data=f"renew_1d_{target_user}"))
        markup.add(types.InlineKeyboardButton("🔄 تجديد 12 ساعة - 0.35$", callback_data=f"renew_12h_{target_user}"))
        markup.add(types.InlineKeyboardButton("🔄 تجديد ساعتين - 0.20$", callback_data=f"renew_2h_{target_user}"))
        # زر تغيير البورت
        markup.add(types.InlineKeyboardButton("🌐 تغيير نوع الاتصال (البورت)", callback_data=f"change_port_{target_user}"))
        # أزرار التنقل
        markup.add(types.InlineKeyboardButton("👨‍💻 الدعم الفني", url=f"tg://user?id={ADMIN_ID}"))
        markup.add(types.InlineKeyboardButton("🔙 العودة لبروكسياتي", callback_data="my_proxies"))
        markup.add(types.InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="main_menu"))
        
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")
    # هذا هو الكود الذي ينفذ فتح الصفحة عند الضغط على الزر
    elif call.data.startswith("p_details_"):
        target_user = call.data.split("_")[2]
        uid = str(call.from_user.id)
        proxy_data = next((sub for sub in active_proxies.get(uid, []) if sub['user'] == target_user), None)
        
        if proxy_data:
            p_id = str(proxy_data['port'])
            
            # خريطة العناوين لضمان ظهور الـ Host الصحيح لكل بورت
            host_map = {
                "23822": "switchback.proxy.rlwy.net",
                "13813": "shuttle.proxy.rlwy.net",
                "13021": "interchange.proxy.rlwy.net",
                "33451": "ballast.proxy.rlwy.net",
                "42177": "maglev.proxy.rlwy.net"
            }
            host_address = host_map.get(p_id, "interchange.proxy.rlwy.net")

            details = (
                f"💙 **Golden Proxy Details** 💙\n"
                f"━━━━━━━━━━━━━━\n"
                f"🌐 **IP/Host:** `{host_address}`\n"
                f"🔢 **Port:** `{p_id}`\n"
                f"👤 **User:** `{proxy_data['user']}`\n"
                f"🔑 **Pass:** `{proxy_data['pass']}`\n"
                f"⚙️ **Type:** `SOCKS5 / HTTP`\n"
                f"━━━━━━━━━━━━━━\n"
                f"📅 **Expiry:** `{proxy_data['expiry']}`\n"
                f"🇺🇸 **Country:** `UNITED STATES`\n"
                f"🏢 **Provider:** `AT&T Internet @ TEXAS`\n"
                f"🔄 **Rotation:** `30 min`\n"
                f"🟢 **Status:** `ACTIVE`\n"
                f"━━━━━━━━━━━━━━\n"
                f"🔹 *انسخ البيانات وضعها في تطبيقك مباشرة.*"
            )
            
            markup = types.InlineKeyboardMarkup().add(
                types.InlineKeyboardButton("🔙 رجوع", callback_data=f"manage_{target_user}")
            )
            
            bot.edit_message_text(
                details, 
                call.message.chat.id, 
                call.message.message_id, 
                reply_markup=markup, 
                parse_mode="Markdown"
            )

    elif call.data.startswith("change_port_"):
        target_user = call.data.split("_")[2]
        text = f"🚀 **اختر البورت الجديد للبروكسي `{target_user}`:**"
        
        markup = types.InlineKeyboardMarkup(row_width=1)
        ports = [("🇺🇸 USA/TEXAS", "11001"), ("🇺🇸 USA/FLORIDA", "11002"), ("🇺🇸 USA/CALIFORNIA", "11003"), ("🇺🇸 USA/NEW YORK", "11004"), ("🇺🇸 USA/GEORGIA", "11005")]
        
        for loc, port in ports:
            markup.add(types.InlineKeyboardButton(f"📍 {loc} | Port: {port}", callback_data=f"setport_{target_user}_{port}"))
        
        markup.add(types.InlineKeyboardButton("🔙 العودة للخلف", callback_data=f"manage_{target_user}"))
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")

    elif call.data.startswith("setport_"):
        uid = str(call.from_user.id)
        data = call.data.split("_")
        target_user = data[1]
        new_port = data[2]
        
        if uid in active_proxies:
            for sub in active_proxies[uid]:
                if sub['user'] == target_user:
                    old_port = sub['port']
                    sub['port'] = new_port # تحديث البورت في الرام
                    break
            save_data() # <<< هذا هو السطر الأهم: سيقوم بتحديث ملف السيرفر فوراً بالبورت الجديد
            bot.answer_callback_query(call.id, f"✅ تم تغيير البورت إلى {new_port} بنجاح!", show_alert=True)
            # لتحديث الرسالة أمام المستخدم بعد التغيير
            main_menu(call.message.chat.id, uid)

        
    elif call.data == "buy_proxy":
        markup = types.InlineKeyboardMarkup(row_width=1)
        # هنا البوت يمر على القاموس ويصنع الأزرار لوحده
        for p_id, info in PORT_DETAILS.items():
            btn_text = f"📍 {info['loc']} | Port: {p_id} | Rot: {info['rotation']}m"
            markup.add(types.InlineKeyboardButton(btn_text, callback_data=f"sel_p_{p_id}"))
        
        markup.add(types.InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="main_menu"))
        bot.edit_message_text("🚀 **اختر البورت المطلوب:**", call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")

    elif call.data == "show_prices":
        text = "💎 **قائمة الأسعار:**\n🟣 يوم: 0.50$\n🔵 12 ساعة: 0.35$\n⚡ ساعتين: 0.20$"
        markup = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("🔙 العودة", callback_data="back"))
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")

    elif call.data == "top_up":
        text = (
            "⚠️ **تعليمات الشحن الهامة**\n\n"
            "1️⃣ اختر وسيلة الدفع المناسبة لك.\n"
            "2️⃣ قم بنسخ **معرف الخدمة** الموضح بالأسفل.\n"
            "3️⃣ **برجاء الانتظار لدقائق بعد الشحن** وإرسال معرف الشحن للبوت.\n\n"
            "👇 **اختر وسيلة الدفع لنسخ المعرف:**"
        )
        markup = types.InlineKeyboardMarkup(row_width=1)
        # استخدمنا chr_ هنا لمنع التضارب مع أزرار الشراء pay_
        markup.add(
            types.InlineKeyboardButton("💳 Vodafone Cash", callback_data="chr_voda"),
            types.InlineKeyboardButton("💳 Binance Pay", callback_data="chr_binance"),
            types.InlineKeyboardButton("💳 FaucetPay", callback_data="chr_faucet"),
            types.InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data="main_menu")
        )
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")
    elif call.data.startswith("chr_"):
        # هذا الجزء يعرض بيانات الدفع بناءً على الزر المضغوط
        pay_info = {
            "chr_voda": "📱 رقم فودافون كاش: `01104640959`",
            "chr_binance": "🆔 Binance ID: `1190017166`",
            "chr_faucet": "📧 FaucetPay: `7ded1021@gmail.com`"
        }
        info_text = pay_info.get(call.data, "⚠️ لا توجد بيانات حالياً.")
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("👨‍💻 مراسلة الإدارة", url=f"tg://user?id={ADMIN_ID}"))
        markup.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="top_up"))
        
        bot.edit_message_text(f"✅ **بيانات الدفع:**\n\n{info_text}", call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")
        

    elif call.data in ["pay_binance", "pay_voda", "pay_fauc"]:
        pay_info = {"pay_binance": "🆔 Binance ID: `1190017166`", "pay_voda": "📱 رقم فودافون: `01104640959`", "pay_fauc": "📧 العنوان: `7ded1021@gmail.com`"}
        markup = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("👨‍💻 مراسلة الإدارة", url=f"tg://user?id={ADMIN_ID}"), types.InlineKeyboardButton("🔙 رجوع", callback_data="top_up"))
        bot.edit_message_text(f"✅ **بيانات الدفع:**\n{pay_info[call.data]}", call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")

    elif call.data.startswith("pay_"):
        data = call.data.split("_")
        if len(data) < 4: return # هذا هو سطر الحماية الأهم لمنع الانهيار
        
        port, plan, price = data[1], data[2], float(data[3])
        # ... باقي كود الشراء كما هو ...

    
        port, plan, price = data[1], data[2], float(data[3])
        if user_balances.get(uid, 0.0) < price:
            bot.answer_callback_query(call.id, "⚠️ رصيدك غير كافٍ!", show_alert=True)
        else:
            msg = bot.send_message(call.message.chat.id, "👤 **أرسل اليوزر نيم المطلوب:**")
            bot.register_next_step_handler(msg, lambda m: get_p_step(m, port, plan, price))

    # --- لوحة التحكم كاملة ---
    elif call.data == "admin_panel" and int(uid) == ADMIN_ID:
        markup = types.InlineKeyboardMarkup(row_width=2).add(
            types.InlineKeyboardButton("➕ شحن", callback_data="adm_add"), types.InlineKeyboardButton("➖ سحب", callback_data="adm_sub"),
            types.InlineKeyboardButton("📢 إذاعة", callback_data="adm_bc"), types.InlineKeyboardButton("📊 النشطين", callback_data="adm_view"),
            types.InlineKeyboardButton("🔍 فحص ID", callback_data="adm_check_id"))
        bot.edit_message_text("🛠 **لوحة التحكم العليا**", call.message.chat.id, call.message.message_id, reply_markup=markup)

    elif call.data == "adm_view" and int(uid) == ADMIN_ID:
        text = "👥 **المستخدمين النشطين:**\n"
        for uk, pxs in active_proxies.items():
            for s in pxs: text += f"?? `{uk}` | 👤 `{s['user']}` | ⏳ `{s['expiry']}`\n"
        bot.edit_message_text(text if len(text)>25 else "لا يوجد نشطين", call.message.chat.id, call.message.message_id, 
                             reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("🔙 العودة", callback_data="admin_panel")), parse_mode="Markdown")

    elif call.data == "adm_add" and int(uid) == ADMIN_ID:
        msg = bot.send_message(call.message.chat.id, "👤 ارسل ID المستخدم:")
        bot.register_next_step_handler(msg, lambda m: get_admin_amount(m, "شحن"))

    elif call.data == "adm_sub" and int(uid) == ADMIN_ID:
        msg = bot.send_message(call.message.chat.id, "👤 ارسل ID المستخدم:")
        bot.register_next_step_handler(msg, lambda m: get_admin_amount(m, "سحب"))

    elif call.data == "adm_bc" and int(uid) == ADMIN_ID:
        msg = bot.send_message(call.message.chat.id, "📢 ارسل رسالة الإذاعة:")
        bot.register_next_step_handler(msg, execute_broadcast)

    elif call.data == "adm_check_id" and int(uid) == ADMIN_ID:
        msg = bot.send_message(call.message.chat.id, "🔍 ارسل الـ ID:")
        bot.register_next_step_handler(msg, process_check_id)

# --- الدوال المساعدة ---
def get_admin_amount(message, action):
    target_id = message.text.strip()
    msg = bot.send_message(ADMIN_ID, f"💰 ادخل المبلغ لـ {action}:")
    bot.register_next_step_handler(msg, finish_admin_action, target_id, action)

def finish_admin_action(message, target_id, action):
    try:
        val = float(message.text)
        if action == "شحن": user_balances[target_id] = round(user_balances.get(target_id, 0.0) + val, 2)
        else: user_balances[target_id] = round(user_balances.get(target_id, 0.0) - val, 2)
        save_data(); bot.send_message(ADMIN_ID, "✅ تم بنجاح."); bot.send_message(target_id, f"🔔 تم {action} مبلغ {val}$")
    except: bot.send_message(ADMIN_ID, "❌ خطأ!")

def execute_broadcast(message):
    for u in list(user_list):
        try: bot.send_message(int(u), message.text)
        except: continue
    bot.send_message(ADMIN_ID, "✅ تم.")

def process_check_id(message):
    tid = message.text.strip()
    bot.send_message(ADMIN_ID, f"🆔 ID: `{tid}`\n💰 رصيد: `{user_balances.get(tid, 0.0)}$`", parse_mode="Markdown")

def get_p_step(message, port, plan, price):
    uname = message.text.strip()
    msg = bot.send_message(message.chat.id, "🔐 **أرسل الباسورد المطلوب:**")
    bot.register_next_step_handler(msg, lambda m: final_gold_create(m, uname, port, plan, price))

def final_gold_create(message, uname, port, plan, price):
    uid = str(message.from_user.id)
    upass = message.text.strip()
    
    if user_balances.get(uid, 0.0) >= price:
        user_balances[uid] -= price
        
        # 1. رسالة الانتظار أثناء المعالجة
        wait_msg = bot.send_message(
            message.chat.id, 
            "⏳ **جاري تهيئة باقتك الذهبية...**",
            parse_mode="Markdown"
        )
        
        # 2. تحديد العنوان (Host) الصحيح بناءً على البورت المختار
        host_map = {
            "23822": "switchback.proxy.rlwy.net",
            "13813": "shuttle.proxy.rlwy.net",
            "13021": "interchange.proxy.rlwy.net",
            "33451": "ballast.proxy.rlwy.net",
            "42177": "maglev.proxy.rlwy.net"
        }
        # جلب العنوان المناسب للبورت، وإذا لم يوجد يستخدم الافتراضي
        host_address = host_map.get(str(port), "interchange.proxy.rlwy.net")
        
        # 3. إعداد البيانات والوقت
        days = 7  # المدة الافتراضية
        if "1d" in plan: days = 1
        elif "12h" in plan: days = 0.5
        
        expiry_date = (datetime.datetime.now() + datetime.timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
        
        new_proxy = {
            "user": uname,
            "pass": upass,
            "port": port,
            "expiry": expiry_date
        }
        
        active_proxies.setdefault(uid, []).append(new_proxy)
        
        # 4. تحديث السيرفر (رفع ملف CFG إلى GitHub)
        save_data()
        
        # 5. الرسالة النهائية (تفاصيل الاستلام) - التصميم الأزرق الفاخر
        success_details = (
            f"💙 **Golden Package Details** 💙\n"
            f"━━━━━━━━━━━━━━\n"
            f"🌐 **IP/Host:** `{host_address}`\n"
            f"🔢 **Port:** `{port}`\n"
            f"👤 **User:** `{uname}`\n"
            f"🔑 **Pass:** `{upass}`\n"
            f"⚙️ **Type:** `SOCKS5 / HTTP`\n"
            f"━━━━━━━━━━━━━━\n"
            f"📅 **Expiry:** `{expiry_date}`\n"
            f"🇺🇸 **Country:** `UNITED STATES`\n"
            f"🏢 **Provider:** `AT&T Internet @ TEXAS`\n"
            f"🔄 **Rotation:** `30 min`\n"
            f"🟢 **Status:** `ACTIVE`\n"
            f"━━━━━━━━━━━━━━\n"
            f"💡 **ملاحظة:** قد يستغرق تفعيل البيانات على السيرفر العالمي حوالي 30 ثانية.\n"
            f"يمكنك دائماً مراجعة بياناتك من قسم **'بروكسياتي'**."
        )
        
        # تحديث رسالة الانتظار بالبيانات النهائية
        bot.edit_message_text(
            success_details, 
            chat_id=message.chat.id,
            message_id=wait_msg.message_id,
            parse_mode="Markdown"
        )
    else:
        bot.send_message(message.chat.id, "⚠️ عذراً، رصيدك غير كافٍ لإتمام العملية!")

@bot.callback_query_handler(func=lambda call: call.data.startswith("pay_"))
def ask_transaction_id(call):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔙 إلغاء والعودة للخلف", callback_data="top_up"))
    msg = bot.send_message(call.message.chat.id, "✅ **تم اختيار الوسيلة.**\n\n📥 **الرجاء إرسال معرف الشحن الخاص بك (رقم العملية أو اسم المحول):**", reply_markup=markup, parse_mode="Markdown")
    bot.register_next_step_handler(msg, process_amount_step)

def process_amount_step(message):
    trans_id = message.text
    msg = bot.send_message(message.chat.id, f"📥 **تم استلام المعرف:** `{trans_id}`\n\n💰 **رجاء إدخال مبلغ الشحن بالأرقام الإنجليزية فقط (مثلاً: 5.50):**")
    bot.register_next_step_handler(msg, final_topup_step, trans_id)

def final_topup_step(message, trans_id):
    amount = message.text
    if not amount.replace('.', '', 1).isdigit():
        msg = bot.send_message(message.chat.id, "❌ خطأ! يرجى إرسال المبلغ بالأرقام الإنجليزية فقط:")
        bot.register_next_step_handler(msg, final_topup_step, trans_id)
        return

    bot.send_message(message.chat.id, "⏳ **قد يستغرق الوقت لدقائق، برجاء الانتظار وسيتم الشحن.**")
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ شحن المبلغ", callback_data=f"approve_{message.from_user.id}_{amount}"))
    markup.add(types.InlineKeyboardButton("❌ رفض", callback_data=f"reject_{message.from_user.id}"))
    
    bot.send_message(ADMIN_ID, f"🔔 **طلب شحن جديد!**\n👤 المستخدم: `{message.from_user.id}`\n🆔 المعرف: `{trans_id}`\n💵 المبلغ: `{amount}$`", reply_markup=markup, parse_mode="Markdown")

# ==========================================
# محرك نظام الشحن والموافقة اليدوية (نهاية الملف)
# ==========================================

# هذا الكود يوضع في آخر سطر بالملف لضمان عمل الأزرار الثلاثة
@bot.callback_query_handler(func=lambda call: call.data.startswith("chr_"))
def start_charge_process(call):
    # تنظيف أي عمليات سابقة
    bot.clear_step_handler_by_chat_id(chat_id=call.message.chat.id)
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔙 إلغاء", callback_data="top_up"))
    
    msg = bot.send_message(
        call.message.chat.id, 
        "✅ **تم اختيار الوسيلة.**\n\n📥 **الرجاء إرسال معرف العملية (رقم التحويل):**",
        reply_markup=markup,
        parse_mode="Markdown"
    )
    # ننتقل للخطوة التالية لاستلام المعرف
    bot.register_next_step_handler(msg, step_get_amount)

def step_get_amount(message):
    tx_id = message.text
    msg = bot.send_message(message.chat.id, f"💰 **المعرف:** `{tx_id}`\n\nأرسل الآن المبلغ بالأرقام الإنجليزية (مثلاً: 5):")
    bot.register_next_step_handler(msg, step_notify_admin, tx_id)

def step_notify_admin(message, tx_id):
    amount = message.text
    bot.send_message(message.chat.id, "⏳ جاري مراجعة طلبك من قبل الأدمن...")
    
    # إرسال طلب للأدمن مع أزرار الموافقة
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ شحن الآن", callback_data=f"adm_ok_{message.from_user.id}_{amount}"))
    
    bot.send_message(
        ADMIN_ID, 
        f"🔔 **طلب شحن!**\n👤 المستخدم: `{message.from_user.id}`\n🆔 المعرف: `{tx_id}`\n💵 المبلغ: `{amount}$` \n\nاضغط موافقة لشحن الحساب تلقائياً.",
        reply_markup=markup,
        parse_mode="Markdown"
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("adm_ok_"))
def finalize_charge(call):
    if call.from_user.id != ADMIN_ID: return
    # تفكيك البيانات: [adm, ok, uid, amount]
    data = call.data.split("_")
    uid = data[2]
    amount = float(data[3])
    
    # تحديث الرصيد
    user_balances[uid] = round(user_balances.get(uid, 0.0) + amount, 2)
    save_data()
    
    bot.edit_message_text(f"✅ تم شحن {amount}$ للمستخدم {uid}", call.message.chat.id, call.message.message_id)
    
    # إرسال رسالة نجاح للمستخدم مع أزرار العودة
    u_markup = types.InlineKeyboardMarkup()
    u_markup.add(types.InlineKeyboardButton("💳 شحن إضافي", callback_data="top_up"),
                 types.InlineKeyboardButton("🔙 العودة", callback_data="main_menu"))
    
    bot.send_message(uid, f"🎉 **تم شحن حسابك بنجاح!**\n💰 القيمة: `{amount}$`", reply_markup=u_markup)



if __name__ == "__main__":
    load_data()
    threading.Thread(target=auto_clean_expired, daemon=True).start()
    print("🚀 البوت يعمل الآن...")
    bot.infinity_polling()
