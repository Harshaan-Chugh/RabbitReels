import pika
import uuid
import argparse
import os
import json
from dotenv import load_dotenv

def main():
    """Sends a prompt job to the scripts-queue."""
    load_dotenv()
    RABBIT_URL = os.getenv("RABBIT_URL", "amqp://guest:guest@localhost:5672/")
    SCRIPTS_QUEUE = os.getenv("SCRIPTS_QUEUE", "scripts-queue")

    parser = argparse.ArgumentParser(description="Send a prompt to RabbitReels.")
    parser.add_argument("prompt", type=str, help="The prompt for the video script.")
    parser.add_argument(
        "--theme",
        type=str,
        default="family_guy",
        choices=["family_guy", "presidents"],
        help="The character theme to use for the dialog."
    )
    args = parser.parse_args()

    try:
        connection = pika.BlockingConnection(pika.URLParameters(RABBIT_URL))
        channel = connection.channel()
        channel.queue_declare(queue=SCRIPTS_QUEUE, durable=True)

        job_id = f"{args.theme}-{uuid.uuid4().hex[:8]}"
        job = {
            "job_id": job_id,
            "prompt": args.prompt,
            "character_theme": args.theme
        }

        channel.basic_publish(
            exchange="",
            routing_key=SCRIPTS_QUEUE,
            body=json.dumps(job),
            properties=pika.BasicProperties(delivery_mode=2) # make message persistent
        )
        print(f"✅ Sent prompt for job '{job_id}' with theme '{args.theme}'")
        print(f"   Prompt: '{args.prompt}'")

    except pika.exceptions.AMQPConnectionError:
        print(f"❌ Could not connect to RabbitMQ at {RABBIT_URL}. Is it running?")
    except Exception as e:
        print(f"❌ An error occurred: {e}")
    finally:
        if 'connection' in locals() and connection.is_open:
            connection.close()

if __name__ == "__main__":
    main()