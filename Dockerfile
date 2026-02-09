FROM alpine:latest

# 1. تثبيت بايثون وبرنامج البروكسي والأدوات اللازمة
RUN apk add --no-cache --repository http://dl-cdn.alpinelinux.org/alpine/edge/testing \
    3proxy \
    python3 \
    py3-pip

# 2. نسخ ملف إعدادات البروكسي للمسار الصحيح
COPY 3proxy.cfg /etc/3proxy.cfg

# 3. نسخ ملفات الكود الخاصة بك
COPY . .

# 4. تثبيت مكتبات البوت (Telebot و Requests)
RUN pip install --no-cache-dir pyTelegramBotAPI requests --break-system-packages

# 5. فتح منفذ البروكسي
EXPOSE 8080

# 6. الأمر النهائي: تشغيل البروكسي في الخلفية ثم تشغيل البوت
CMD 3proxy /etc/3proxy.cfg && python3 main.py
