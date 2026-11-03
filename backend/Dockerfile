FROM python:3.11-slim

WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev && \
    rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --no-cache-dir --default-timeout=300 torch==2.1.1 --index-url https://download.pytorch.org/whl/cpu
RUN pip install --no-cache-dir --default-timeout=300 -r requirements.txt
COPY backend/ ./backend/
COPY ml/ ./ml/

ENV PYTHONPATH=/app/backend
WORKDIR /app/backend

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

