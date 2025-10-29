FROM python:3.9-slim

# ---- Environment --------------------------------------------------------
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=5000

# ---- Install Chromium system dependencies -------------------------------
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        ca-certificates \
        fonts-liberation \
        libasound2 \
        libatk-bridge2.0-0 \
        libatk1.0-0 \
        libc6 \
        libcairo2 \
        libcups2 \
        libdbus-1-3 \
        libexpat1 \
        libfontconfig1 \
        libgbm1 \
        libglib2.0-0 \
        libgtk-3-0 \
        libnspr4 \
        libnss3 \
        libpango-1.0-0 \
        libpangocairo-1.0-0 \
        libstdc++6 \
        libx11-6 \
        libx11-xcb1 \
        libxcb1 \
        libxcomposite1 \
        libxcursor1 \
        libxdamage1 \
        libxext6 \
        libxfixes3 \
        libxi6 \
        libxrandr2 \
        libxrender1 \
        libxtst6 \
        wget \
        xdg-utils \
    && rm -rf /var/lib/apt/lists/*

# ---- Disable IPv6 to fix ENETUNREACH -----------------------------------
RUN echo 'net.ipv6.conf.all.disable_ipv6 = 1' >> /etc/sysctl.conf && \
    echo 'net.ipv6.conf.default.disable_ipv6 = 1' >> /etc/sysctl.conf && \
    sysctl -p

# ---- Working directory --------------------------------------------------
WORKDIR /app

# ---- Install Python packages --------------------------------------------
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ---- Download Chromium (IPv4 only now) ----------------------------------
RUN playwright install chromium

# ---- Copy app -----------------------------------------------------------
COPY app.py .

# ---- Expose ------------------------------------------------------------
EXPOSE 5000

# ---- Start with Gunicorn ------------------------------------------------
CMD exec gunicorn --bind 0.0.0.0:$PORT \
               --workers 2 \
               --threads 2 \
               --worker-class sync \
               --log-level info \
               app:app
