import json
import pika # type: ignore
import os
from dotenv import load_dotenv # type: ignore

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../.env"))

RABBIT_URL    = os.getenv("RABBIT_URL")
SCRIPTS_QUEUE = os.getenv("SCRIPTS_QUEUE", "scripts-queue")

def publish_prompt(job_id: str, prompt: str):
    conn = pika.BlockingConnection(pika.URLParameters(RABBIT_URL))
    ch   = conn.channel()
    ch.queue_declare(queue=SCRIPTS_QUEUE, durable=True)

    message = {"job_id": job_id, "prompt": prompt}
    ch.basic_publish(
        exchange="",
        routing_key=SCRIPTS_QUEUE,
        body=json.dumps(message),
        properties=pika.BasicProperties(delivery_mode=2)
    )
    print(f"✅ Published prompt `{prompt}` as job_id `{job_id}`")
    conn.close()

if __name__ == "__main__":
    publish_prompt(
        job_id="test-1",
        prompt="Explain Bloom filters in 20 seconds"
    )
