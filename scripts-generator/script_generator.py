import json
import pika # type: ignore
from openai import OpenAI # type: ignore
from common.schemas import PromptJob, DialogJob, Turn
from config import *

client = OpenAI(api_key=OPENAI_API_KEY)

def make_script(prompt_text: str) -> str:
    response = client.chat.completions.create(
        model="gpt-4.1-nano",
        messages=[
            { "role": "system",
              "content": (
                  "You are a social-media-savvy CS educator creating ultra-concise YouTube Shorts scripts. "
                  "Each script must be around 30 seconds long, and follow a structure like:\n"
                  "1. Hook\n"
                  "2. Core Explanation (Go from basic to deep into at least one cool area of the topic and leave the beginner viewers feeling like a topic expert)\n"
                  "Use energetic, direct language; no fluff; end with a call to action and follow for more."
              )
            },
            {
                "role": "user",
                "content": (
                    f"Create a script for: **{prompt_text}**\n"
                    "- Total length: 30 seconds\n"
                    "- Follow the structure given\n"
                    "- No bullet points"
                )
            }
        ],
        temperature=0.6,
        max_tokens=250
    )
    return response.choices[0].message.content.strip()


def make_dialog(prompt_text: str) -> list[dict]:
    """Return a list of {speaker,text} turns ~30 s total."""
    response = client.chat.completions.create(
        model="gpt-4.1-nano",
        messages=[
            {"role": "system", "content": (
                "Write a 30-second YouTube Shorts dialog.\n"
                "Stewie asks snarky, curious questions, Peter answers clearly.\n"
                "Alternate speakers each turn; finish with Stewie excited.\n"
                "Return *ONLY* JSON like:\n"
                "[{\"speaker\":\"stewie\",\"text\":\"...\"}, …]"
            )},
            {"role": "user", "content": prompt_text}
        ],
        temperature=0.7,
        max_tokens=300
    )
    return json.loads(response.choices[0].message.content)


def make_title(prompt_text: str) -> str:
    response = client.chat.completions.create(
        model="gpt-4.1-nano",
        messages=[
            {"role":"system",
             "content":(
               "You are a YouTube Shorts title generator. "
               "Produce a catchy, under-8-word title summarizing the topic."
             )
            },
            {"role":"user", "content":prompt_text}
        ],
        temperature=0.7,
        max_tokens=8
    )
    return response.choices[0].message.content.strip()

def on_message(ch, method, props, body):
    job = PromptJob.model_validate_json(body)
    try:
        turns  = [Turn(**t) for t in make_dialog(job.prompt)]
        title = make_title(job.prompt)
        out_msg = DialogJob(
            job_id=job.job_id,
            title=title,
            turns=turns
        ).model_dump_json()


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
