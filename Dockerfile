FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/
COPY SETTINGS.example.py ./SETTINGS.example.py

# Create data directory
RUN mkdir -p /app/data/audio_cache

# Expose port
EXPOSE 5000

# Run application
CMD ["python", "-m", "app.main"]
