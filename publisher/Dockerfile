FROM python:3.11-slim
WORKDIR /app

# 1) Install dependencies
COPY publisher/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 2) Copy only the code for this service
COPY publisher/publisher.py .
COPY publisher/config.py         .

# 3) Copy shared code
COPY common ./common

# Note: credentials.json & youtube-token.json live in /app/publisher via the
#       directory mount you set up, and your config.py points at their paths.
CMD ["python", "-u", "publisher.py"]
