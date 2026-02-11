FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
  git \
  build-essential \
  cmake \
  ffmpeg \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install whisper.cpp
RUN git clone https://github.com/ggerganov/whisper.cpp.git && \
  cd whisper.cpp && \
  make

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "transcription_service.py"]