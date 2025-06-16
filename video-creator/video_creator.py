# video-creator/video_creator.py
import os
import json
import pika            # type: ignore
from common.schemas import ScriptJob, RenderJob
from config import RABBIT_URL, VIDEO_QUEUE, PUBLISH_QUEUE, VIDEO_OUT_DIR


def render_video(job: ScriptJob) -> str:
    """
    Dummy renderer: just touch an empty MP4 so downstream
    agents can find the file. Replace this with TTS + ffmpeg later.
    """
    os.makedirs(VIDEO_OUT_DIR, exist_ok=True)
    out_path = os.path.join(VIDEO_OUT_DIR, f"{job.job_id}.mp4")

    # write one zero-byte (acts as a stub MP4)
    with open(out_path, "wb") as f:
        f.write(b"\x00")

    return out_path


def on_message(ch, method, props, body):
    job = ScriptJob.model_validate_json(body)

    try:
        video_path = render_video(job)

        render_msg = RenderJob(
            job_id=job.job_id,
            title=job.title,
            storage_path=video_path
        ).model_dump_json()

        ch.basic_publish(
            exchange="",
            routing_key=PUBLISH_QUEUE,
            body=render_msg,
            properties=pika.BasicProperties(delivery_mode=2)
        )

        ch.basic_ack(method.delivery_tag)
        print(f"[✓] Rendered stub video for {job.job_id}")

    except Exception as e:
        print(f"[✗] Rendering failed for {job.job_id}: {e}")
        ch.basic_nack(method.delivery_tag, requeue=False)


def main():
    conn = pika.BlockingConnection(pika.URLParameters(RABBIT_URL))
    ch = conn.channel()

    ch.queue_declare(queue=VIDEO_QUEUE, durable=True)
    ch.queue_declare(queue=PUBLISH_QUEUE, durable=True)

    ch.basic_qos(prefetch_count=1)
    ch.basic_consume(queue=VIDEO_QUEUE, on_message_callback=on_message)

    print("🚀 Video Creator waiting for scripts…")
    ch.start_consuming()


if __name__ == "__main__":
    main()
