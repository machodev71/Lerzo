# Dockerfile
FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Run with Gunicorn (not Flask dev server)
CMD ["gunicorn", "-b", "0.0.0.0:8000", "app:app"]
