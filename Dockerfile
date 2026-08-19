FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu torch torchvision \
    && pip install --no-cache-dir -r requirements.txt gunicorn==23.0.0

COPY . .

ENV COLORHUNT_WARMUP=1
EXPOSE 8000

CMD ["gunicorn", "--workers", "1", "--threads", "4", "--timeout", "60", "--bind", "0.0.0.0:8000", "app:app"]
