FROM python:3.11-slim-bookworm

# System dependencies for Kivy + SDL2 + X11 rendering
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    python3-dev \
    libsdl2-dev \
    libsdl2-image-dev \
    libsdl2-mixer-dev \
    libsdl2-ttf-dev \
    libgl1-mesa-dev \
    libgles2-mesa-dev \
    libgstreamer1.0-dev \
    libmtdev1 \
    libinput-dev \
    xclip \
    xsel \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies first (layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user with video/input group access
RUN useradd -m -s /bin/bash uiuser && \
    usermod -aG video,input uiuser && \
    mkdir -p /var/log && \
    touch /var/log/meetingbox-ui.log && \
    chown uiuser:uiuser /var/log/meetingbox-ui.log && \
    mkdir -p /data/config && \
    chown -R uiuser:uiuser /data/config

USER uiuser

# Kivy environment configuration
ENV KIVY_NO_CONSOLELOG=1
ENV KIVY_WINDOW=sdl2
ENV KIVY_GL_BACKEND=sdl2
ENV KIVY_TEXT=sdl2
ENV KIVY_IMAGE=sdl2

CMD ["python", "src/main.py"]
