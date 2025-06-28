FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy API code
COPY api/main.py .
COPY api/config.py .
COPY api/auth.py .
COPY api/billing.py .
COPY api/user_models.py .
COPY api/database.py .

# Copy shared code
COPY common ./common

# Copy static files
COPY api/static ./static

RUN mkdir -p /app/static

# Expose port
EXPOSE 8080

# Command to run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
