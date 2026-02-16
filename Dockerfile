FROM python:3.10-slim

# FFmpeg yükle
RUN apt-get update && \
    apt-get install -y ffmpeg && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Gereksinimleri yükle
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Kod dosyalarını kopyala
COPY . .

# Port
EXPOSE 8000

# Uygulamayı başlat
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
