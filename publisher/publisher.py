import os, time
import pika  # type: ignore
import json
from google.auth.transport.requests import Request  # type: ignore
from google.oauth2.credentials import Credentials  # type: ignore
from google_auth_oauthlib.flow import InstalledAppFlow  # type: ignore
from googleapiclient.discovery import build  # type: ignore
from googleapiclient.http import MediaFileUpload  # type: ignore
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
    media = MediaFileUpload(
        path,
        chunksize=256 * 1024,  # 256KB chunks for resumable upload
        resumable=True
    )
    request = yt.videos().insert(
        part="snippet,status",
        body={
            "snippet": {
                "title": f"{title} #Shorts",
                "description": "CS/Tech Explained in 30 seconds. Subscribe! #Shorts",
                "tags": ["CS", "Shorts"],
                "categoryId": "27"
            },
            "status": {
                "privacyStatus": "public",
                "selfDeclaredMadeForKids": True
            }
        },
        media_body=media
    )

    response = None
    retry = 0
    max_retries = 5
    while response is None:
        try:
            status, response = request.next_chunk()
            if status:
                print(f" Upload {int(status.progress() * 100)}%")
        except Exception as e:
            retry += 1
            if retry > max_retries:
                raise
            sleep_time = 2 ** retry
            print(f"[!] Error during upload: {e}. Retrying in {sleep_time}s... ({retry}/{max_retries})")
            time.sleep(sleep_time)
    return response["id"]


def on_message(ch, method, props, body):
    job = RenderJob.model_validate_json(body)
    video_path = os.path.join(VIDEOS_DIR, f"{job.job_id}.mp4")
    print(f"[→] Uploading {video_path} as '{job.title}' …")
    try:
        vid_id = upload_to_youtube(video_path, job.title)
        print(f"[✓] Uploaded → https://youtu.be/{vid_id}")
        ch.basic_ack(delivery_tag=method.delivery_tag)
        print("🚀 Publisher waiting for videos…")
    except Exception as e:
        print(f"[✗] Upload failed after retries: {e}")
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)


def main():
    conn = pika.BlockingConnection(pika.URLParameters(RABBIT_URL))
    ch = conn.channel()
    ch.queue_declare(queue=PUBLISH_QUEUE, durable=True)
    ch.basic_qos(prefetch_count=1)
    ch.basic_consume(queue=PUBLISH_QUEUE, on_message_callback=on_message)

    print("🚀 Publisher waiting for videos…")
    ch.start_consuming()


if __name__ == "__main__":
    main()