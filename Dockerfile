FROM python:3.11-slim

RUN useradd -m appuser

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY bot/ ./bot/

RUN chown -R appuser:appuser /app

USER appuser

CMD ["python", "bot/main.py"]