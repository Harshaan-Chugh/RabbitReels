# Publisher

Consumes `RenderJob` from `publish-queue`, picks up the MP4 from `data/videos/{job_id}.mp4`, and uploads it to YouTube.

## Setup

1. Place OAuth2 `credentials.json` in this folder.
2. `pip install -r requirements.txt`
3. On first run, follow the console flow to authorize and save `youtube-token.json`.