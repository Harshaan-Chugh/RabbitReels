import json
import pika
import openai
from common.schemas import PromptJob, ScriptJob
from config import *

openai.api_key = OPENAI_API_KEY

def make_script(prompt_text: str) -> str:
    resp = openai.ChatCompletion.create(
        model="gpt-4.1-nano",
        messages=[
            {"role": "system", "content": "You explain CS concepts in 20 seconds."},
            {"role": "user",   "content": f"Explain `{prompt_text}` in a 15–30s script that will be used for a YouTube short."}
        ],
        temperature=0.7,
        max_tokens=200
    )
    return resp.choices[0].message.content.strip()

def on_message(ch, method, props, body):
    job = PromptJob.parse_raw(body)
    try:
        script = make_script(job.prompt)
        out_msg = ScriptJob(
            job_id=job.job_id,
            title = job.title or job.prompt,
            script=script
        ).json()
        ch.basic_publish(
            exchange="",
            routing_key=VIDEO_QUEUE,
            body=out_msg,
            properties=pika.BasicProperties(delivery_mode=2)
        )
        ch.basic_ack(delivery_tag=method.delivery_tag)
        print(f"[✓] Generated script for {job.job_id}")
    except Exception as e:
        print(f"[✗] Failed {job.job_id}: {e}")
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

def main():
    conn = pika.BlockingConnection(pika.URLParameters(RABBIT_URL))
    ch   = conn.channel()
    ch.queue_declare(queue=SCRIPTS_QUEUE, durable=True)
    ch.queue_declare(queue=VIDEO_QUEUE,   durable=True)
    ch.basic_qos(prefetch_count=1)
    ch.basic_consume(queue=SCRIPTS_QUEUE, on_message_callback=on_message)
    print("Waiting for prompts…")
    ch.start_consuming()

if __name__ == "__main__":
    main()
