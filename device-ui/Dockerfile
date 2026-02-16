FROM python:3.11-slim

# ---------------------------------------------------------------
# System dependencies for Kivy GUI on Raspberry Pi (X11 backend)
# ---------------------------------------------------------------
RUN apt-get update && apt-get install -y --no-install-recommends \
    # SDL2 (Kivy rendering backend)
    libsdl2-dev \
    libsdl2-image-dev \
    libsdl2-mixer-dev \
    libsdl2-ttf-dev \
    # OpenGL
    libgl1-mesa-dev \
    libgles2-mesa-dev \
    libegl1-mesa-dev \
    # X11 client libs (to connect to the host X server)
    libx11-dev \
    libxext-dev \
    libxrender-dev \
    libxcursor-dev \
    libxfixes-dev \
    libxi-dev \
    libxrandr-dev \
    # GStreamer (Kivy media)
    libgstreamer1.0-dev \
    gstreamer1.0-plugins-base \
    # Input (touch)
    libmtdev1 \
    libinput-dev \
    # Build tools
    build-essential \
    pkg-config \
    # Misc
    xdg-utils \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps first (better layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user for security
RUN useradd -m -s /bin/bash uiuser \
    && chown -R uiuser:uiuser /app

# Kivy config: use SDL2 window provider, disable console log
ENV KIVY_WINDOW=sdl2
ENV KIVY_NO_CONSOLELOG=1
ENV KIVY_LOG_LEVEL=info
ENV PYTHONUNBUFFERED=1

USER uiuser

CMD ["python", "src/main.py"]
