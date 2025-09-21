FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# IMPORTANT: point to app:app, not main:app
CMD ["gunicorn", "-b", "0.0.0.0:8000", "app:app"]
