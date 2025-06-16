import os, sys
import pika
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
VIDEOS_DIR = os.path.join(BASE_DIR, "data", "videos")

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from common.schemas import RenderJob
from config import RABBIT_URL, PUBLISH_QUEUE, VIDEOS_DIR, CLIENT_SECRETS, TOKEN_PATH

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

def get_youtube_client():
    creds = None
    if os.path.exists(TOKEN_PATH) and os.path.getsize(TOKEN_PATH) > 0:
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS, SCOPES)
            creds = flow.run_local_server(port=0)
        
        with open(TOKEN_PATH, "w") as f:
            f.write(creds.to_json())

    return build("youtube", "v3", credentials=creds)

yt = get_youtube_client()

def upload_to_youtube(path: str, title: str):
    media = MediaFileUpload(path, chunksize=-1, resumable=True)
    request = yt.videos().insert(
        part="snippet,status",
        body={
            "snippet": {"title": title, "description": "", "tags": ["CS"], "categoryId": "27"},
            "status":  {"privacyStatus": "public", "selfDeclaredMadeForKids": True}
        },
        media_body=media
    )
    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f" Upload {int(status.progress()*100)}%")
    return response["id"]

def on_message(ch, method, props, body):
    job = RenderJob.model_validate_json(body)
    video_path = os.path.join(VIDEOS_DIR, f"{job.job_id}.mp4")
    print(f"[→] Uploading {video_path} as '{job.title}' …")
    try:
        vid_id = upload_to_youtube(video_path, job.title)
        print(f"[✓] Uploaded → https://youtu.be/{vid_id}")
        ch.basic_ack(delivery_tag=method.delivery_tag)
    except Exception as e:
        print(f"[✗] Upload failed: {e}")
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

def main():
    conn = pika.BlockingConnection(pika.URLParameters(RABBIT_URL))
    ch   = conn.channel()
    ch.queue_declare(queue=PUBLISH_QUEUE, durable=True)
    ch.basic_qos(prefetch_count=1)
    ch.basic_consume(queue=PUBLISH_QUEUE, on_message_callback=on_message)
    print("🚀 Publisher waiting for videos…")
    ch.start_consuming()

if __name__ == "__main__":
    main()
