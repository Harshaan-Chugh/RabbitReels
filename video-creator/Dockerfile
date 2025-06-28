FROM python:3.11-slim

RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        imagemagick ghostscript fonts-liberation fonts-dejavu-core ffmpeg \
        fontconfig fonts-liberation2 fonts-dejavu fonts-dejavu-extra && \
    # Fix ImageMagick security policy for MoviePy text rendering
    sed -i 's/rights="none" pattern="TEXT"/rights="read|write" pattern="TEXT"/' /etc/ImageMagick-6/policy.xml && \
    sed -i 's/rights="none" pattern="LABEL"/rights="read|write" pattern="LABEL"/' /etc/ImageMagick-6/policy.xml && \
    sed -i 's/rights="none" pattern="CAPTION"/rights="read|write" pattern="CAPTION"/' /etc/ImageMagick-6/policy.xml && \
    sed -i 's/rights="none" pattern="@\*"/rights="read|write" pattern="@*"/' /etc/ImageMagick-6/policy.xml && \
    fc-cache -fv && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

ENV IMAGEMAGICK_BINARY=/usr/bin/convert

WORKDIR /app

COPY video-creator/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY video-creator/video_creator.py .
COPY video-creator/config.py        .
COPY common ./common
COPY video-creator/assets ./assets

CMD ["python", "-u", "video_creator.py"]