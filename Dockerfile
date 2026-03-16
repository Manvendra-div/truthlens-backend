FROM python:3.11-slim

WORKDIR /app

# install system deps
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# copy requirements
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# copy backend code
COPY . .

# expose FastAPI port
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]