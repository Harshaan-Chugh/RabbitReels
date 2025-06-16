FROM python:3.11-slim

# 1) Set working directory
WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY publisher.py config.py README.md ./

COPY ../common ../common

COPY credentials.json youtube-token.json ./

CMD ["python", "publisher.py"]
