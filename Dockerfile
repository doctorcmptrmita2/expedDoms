# ExpiredDomain.dev - FastAPI Application Dockerfile
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    default-libmysqlclient-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Copy check scripts
COPY check_container.sh /app/check_container.sh
RUN chmod +x /app/check_container.sh
COPY check_db_connection.py /app/check_db_connection.py
RUN chmod +x /app/check_db_connection.py

# Create data directory for zone files
RUN mkdir -p /app/data/zones

# Expose port
EXPOSE 8000

# Health check (using Python's urllib instead of curl)
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health').read()" || exit 1

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

