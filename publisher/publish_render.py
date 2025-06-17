import os, json, pika                            # type: ignore
from dotenv import load_dotenv                   # type: ignore

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../.env"))

conn = pika.BlockingConnection(pika.URLParameters("amqp://guest:guest@localhost:5672/"))
ch   = conn.channel()
ch.queue_declare(queue=os.getenv("PUBLISH_QUEUE"), durable=True)

job = {
    "job_id":       "test-pub",
    "title":        "Dummy Test Upload 🔥",
    "storage_path": "data/videos/test-pub.mp4"
}

ch.basic_publish(
    exchange="",
    routing_key=os.getenv("PUBLISH_QUEUE"),
    body=json.dumps(job),
    properties=pika.BasicProperties(delivery_mode=2)
)
print("✅ Published dummy RenderJob to publish-queue")
conn.close()
