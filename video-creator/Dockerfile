FROM python:3.11-slim
WORKDIR /app

RUN apt-get update && \
    apt-get install -y ffmpeg && \
    rm -rf /var/lib/apt/lists/*

COPY video-creator/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY video-creator/video_creator.py .
COPY video-creator/config.py        .
COPY common ./common

CMD ["python", "-u", "video_creator.py"]
