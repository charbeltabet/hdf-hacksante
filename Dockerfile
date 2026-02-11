FROM python:3.11-slim

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        gcc \
        libffi-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn

COPY . .

EXPOSE 7500

CMD ["gunicorn", "--bind", "0.0.0.0:7500", "--workers", "2", "--threads", "4", "--timeout", "120", "app:app"]
