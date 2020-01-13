FROM alpine:3.10
LABEL maintainer wangkexiong<wangkexiong@gmail.com>

ADD . /working
WORKDIR /working

RUN apk add --no-cache chromium chromium-chromedriver python3 \
    && pip3 install --no-cache-dir -r requirements.txt \
    && find /usr/lib | grep -E "(__pycache__|\.pyc|\.pyo$)" | xargs rm -rf
