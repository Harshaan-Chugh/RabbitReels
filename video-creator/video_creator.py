import os, json
import pika # type: ignore
from common.schemas import ScriptJob, RenderJob
from config import RABBIT_URL, VIDEO_QUEUE, PUBLISH_QUEUE, VIDEO_OUT_DIR

def render_video(job: ScriptJob) -> str:
    os.makedirs(VIDEO_OUT_DIR, exist_ok=True)
    out_path = os.path.join(VIDEO_OUT_DIR, f"{job.job_id}.mp4")
    # TODO: Replace with actual video-generation call
    # e.g. revid_client.create_video(script=job.script, output_path=out_path)
    with open(out_path, "wb") as f:
        f.write(b"\x00")  # dummy byte so file exists
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
        ch.basic_ack(delivery_tag=method.delivery_tag)
        print(f"[✓] Rendered video for {job.job_id}")
    except Exception as e:
        print(f"[✗] Rendering failed for {job.job_id}: {e}")
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

def main():
    conn = pika.BlockingConnection(pika.URLParameters(RABBIT_URL))
    ch   = conn.channel()
    ch.queue_declare(queue=VIDEO_QUEUE,   durable=True)
    ch.queue_declare(queue=PUBLISH_QUEUE, durable=True)
    ch.basic_qos(prefetch_count=1)
    ch.basic_consume(queue=VIDEO_QUEUE, on_message_callback=on_message)
    print("Video Creator waiting for scripts…")
    ch.start_consuming()

if __name__ == "__main__":
    main()
