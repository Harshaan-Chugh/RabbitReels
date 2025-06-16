FROM python:3.11-slim
WORKDIR /app

# 1) Install dependencies
COPY video-creator/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 2) Copy only the code for this service
COPY video-creator/video_creator.py .
COPY video-creator/config.py        .

# 3) Copy shared code
COPY common ./common

CMD ["python", "video_creator.py"]
