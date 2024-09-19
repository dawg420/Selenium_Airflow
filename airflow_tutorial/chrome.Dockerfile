FROM python:3.9.13-alpine

EXPOSE 5900

COPY ./requirements.txt /tmp/requirements.txt
COPY ./dags/scripts /scripts
COPY ./dags/app /app

# Install temporary dependencies
RUN apk update && apk upgrade && \
    apk add --no-cache --virtual .build-deps \
    alpine-sdk \
    curl \
    wget \
    unzip \
    gnupg 

# Install dependencies
RUN apk add --no-cache \
    xvfb \
    x11vnc \
    fluxbox \
    xterm \
    libffi-dev \
    bzip2-dev \
    bzip2 \
    git \
    nss \
    freetype \
    freetype-dev \
    harfbuzz \
    ca-certificates \
    ttf-freefont \
    chromium \
    chromium-chromedriver

RUN python -m pip install --upgrade pip

# Install Python dependencies
RUN pip install --no-cache-dir --no-deps -r /tmp/requirements.txt && \
    rm /tmp/requirements.txt

WORKDIR /app

RUN chmod -R +x /scripts

ENV PATH="/scripts:$PATH"
ENV DISPLAY=:0

# Delete temporary dependencies
RUN apk del .build-deps

CMD ["tail", "-f", "/dev/null"]