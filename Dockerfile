# ---- Base image ---------------------------------------------------------
FROM python:3.9-slim

# ---- Environment --------------------------------------------------------
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=5000

# ---- Install system packages needed for Chromium -----------------------
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
        libgcc1 \
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
        lsb-release \
        wget \
        xdg-utils \
    && rm -rf /var/lib/apt/lists/*

# ---- Working directory --------------------------------------------------
WORKDIR /app

# ---- Python dependencies ------------------------------------------------
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ---- Playwright browsers ------------------------------------------------
# (install-deps is not needed because we installed the apt packages above)
RUN playwright install chromium

# ---- Application code ---------------------------------------------------
COPY app.py .

# ---- Expose port (Render will override with $PORT) --------------------
EXPOSE 5000

# ---- Start command (Gunicorn) -------------------------------------------
#   - 2 workers + 1 thread per worker works well on Render's free tier
#   - Bind to $PORT (Render sets this env var)
CMD exec gunicorn --bind 0.0.0.0:$PORT \
               --workers 2 \
               --threads 2 \
               --worker-class sync \
               --log-level info \
               app:app
