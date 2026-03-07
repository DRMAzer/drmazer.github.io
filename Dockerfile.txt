FROM alpine:latest

RUN apk add --no-cache --repository http://dl-cdn.alpinelinux.org/alpine/edge/testing \
    3proxy \
    python3 \
    py3-pip

WORKDIR /app
COPY . .

RUN pip install --no-cache-dir pyTelegramBotAPI requests --break-system-packages

RUN mkdir -p /etc/3proxy
RUN cp 3proxy.cfg /etc/3proxy/3proxy.cfg

EXPOSE 8080

CMD 3proxy /etc/3proxy/3proxy.cfg && python3 main.py
