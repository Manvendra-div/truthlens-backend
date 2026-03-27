FROM python:3.14-slim

# system deps
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# install CPU-only torch first — this alone saves ~3GB vs default torch
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

# install rest of dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# copy app code
COPY app/ ./app/
COPY alembic/ ./alembic/
COPY alembic.ini .

# copy model
COPY truthlens_fake_news_model/ ./truthlens_fake_news_model/

EXPOSE 8000

CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
