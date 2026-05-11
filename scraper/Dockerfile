FROM python:3.11-slim

# Installe Chrome + dépendances système
RUN apt-get update && apt-get install -y \
    wget \
    gnupg2 \
    ca-certificates \
    apt-transport-https \
    && wget -q -O - https://dl.google.com/linux/linux_signing_key.pub \
       | gpg --dearmor > /usr/share/keyrings/google.gpg \
    && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google.gpg] \
       http://dl.google.com/linux/chrome/deb/ stable main" \
       > /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Les données scrapées sont montées en volume (local) ou uploadées en S3 (prod)
VOLUME ["/app/data"]

CMD ["python", "main.py"]
