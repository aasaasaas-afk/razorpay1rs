FROM mcr.microsoft.com/playwright/python:v1.47.2-jammy

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=5000

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000

CMD exec gunicorn --bind 0.0.0.0:$PORT \
               --workers 2 \
               --threads 2 \
               --worker-class sync \
               --log-level info \
               app:app
