FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY monitor.py .
COPY config.py .

# Copy shared schemas
COPY ../common ./common

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import redis; r = redis.from_url('$REDIS_URL'); r.ping()" || exit 1

# Command to run the application
CMD ["python", "-u", "monitor.py"] 