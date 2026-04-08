FROM python:3.11-slim

# Sistem bağımlılıkları (pyodbc için build tools)
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    unixodbc-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Önce bağımlılıkları kopyala — layer cache için
COPY pyproject.toml requirements.txt ./

# Tüm DB driver'ları ile kur
RUN pip install --no-cache-dir -e ".[all-db]"

# Uygulama kodunu kopyala
COPY . .

# Annotations klasörü volume mount noktası
RUN mkdir -p /app/annotations

EXPOSE 11234

# Flask'ın tüm interface'leri dinlemesi için host 0.0.0.0
CMD ["dbtellme", "ui", "--port", "11234", "--host", "0.0.0.0"]
