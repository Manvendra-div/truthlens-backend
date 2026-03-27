FROM python:3.11-slim AS base

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

COPY . .

RUN rm -rf /root/.cache

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]