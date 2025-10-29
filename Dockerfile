# Use official Playwright image that already includes Chromium
FROM mcr.microsoft.com/playwright/python:v1.47.2-jammy

# ---- Environment --------------------------------------------------------
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=5000 \
    NODE_OPTIONS=--dns-result-order=ipv4first

# ---- Working directory --------------------------------------------------
WORKDIR /app

# ---- Copy dependencies --------------------------------------------------
COPY requirements.txt .

# ---- Install Python dependencies ----------------------------------------
RUN pip install --no-cache-dir -r requirements.txt

# ---- Copy app files -----------------------------------------------------
COPY . .

# ---- Expose app port ----------------------------------------------------
EXPOSE 5000

# ---- Start Gunicorn -----------------------------------------------------
CMD exec gunicorn --bind 0.0.0.0:$PORT \
               --workers 2 \
               --threads 2 \
               --worker-class sync \
               --log-level info \
               app:app
