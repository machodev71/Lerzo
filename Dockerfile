# Use Python base image
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Copy dependencies
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Expose port (Flask default 5000 but Dokploy uses 80/443 externally)
EXPOSE 5000

# Run with Gunicorn, pointing to your Flask app inside main.py
# If you have app = Flask(__name__) in main.py, then use main:app
CMD ["gunicorn", "-b", "0.0.0.0:5000", "main:app"]
