import json
import pika # type: ignore
from openai import OpenAI # type: ignore
from common.schemas import PromptJob, DialogJob, Turn
from config import *

client = OpenAI(api_key=OPENAI_API_KEY)

CHARACTER_CONFIG = {
    "family_guy": {
        "char1_name": "stewie",
        "char1_persona": "snarky and curious",
        "char2_name": "peter",
        "char2_persona": "the dim-witted, though well-meaning and great explainer",
        "starter": "stewie"
    },
    "rick_and_morty": {
        "char1_name": "rick",
        "char1_persona": "brilliant but cynical scientist who explains things condescendingly and calls Morty 'Morty' or 'dummy'",
        "char2_name": "morty",
        "char2_persona": "nervous, questioning teenager who asks lots of questions and stutters, addresses Rick as 'Rick' or 'Aw geez Rick'",
        "starter": "morty"
    }
}

def make_script(prompt_text: str) -> str:
    response = client.chat.completions.create(
        model="gpt-4.1-nano",
        messages=[
            { "role": "system",
              "content": (
                  "You are a social-media-savvy CS educator creating ultra-concise YouTube Shorts scripts. "
                  "Each script must be around 30-40 seconds long, and follow a structure like:\n"
                  "1. Hook\n"
                  "2. Core Explanation (Go from basic to deep into at least one cool area of the topic and leave the beginner viewers feeling like a topic expert)\n"
                  "Use energetic, direct language; no fluff; end with a call to action and follow for more."
              )
            },
            {
                "role": "user",
                "content": (
                    f"Create a script for: **{prompt_text}**\n"
                    "- Total length: 30-40 seconds\n"
                    "- Follow the structure given\n"
                    "- No bullet points"
                )
            }
        ],
        temperature=0.6,
        max_tokens=250
    )
    return response.choices[0].message.content.strip()


def make_dialog(prompt_text: str, theme: str) -> list[dict]:
    """Return a list of {speaker,text} turns ~30 s total for a given theme."""
    config = CHARACTER_CONFIG.get(theme)
    if not config:
        raise ValueError(f"Invalid character theme: {theme}")

    system_prompt = (
        f"You are a scriptwriter for a YouTube Short. Write a 30-second dialog between {config['char1_name']} and {config['char2_name']}.\n"
        f"{config['char1_name'].title()} is {config['char1_persona']}.\n"
        f"{config['char2_name'].title()} is {config['char2_persona']}.\n"
        f"The dialog must alternate speakers, starting with {config['starter']}.\n"
        "You MUST return a valid JSON object. The root object must have a single key, 'dialog', which is a JSON array of turn objects.\n"
        "Each turn object in the array MUST have exactly two keys: 'speaker' (string name) and 'text' (string: the character's line)."
    )

    response = client.chat.completions.create(
        model="gpt-4.1-nano",
        response_format={"type": "json_object"}, # Enforce JSON mode
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Create a dialog about: {prompt_text}"}
        ],
        temperature=0.7,
        max_tokens=400
    )
    
    try:
        response_data = json.loads(response.choices[0].message.content)
        turns_list = response_data.get("dialog")
        
        if not isinstance(turns_list, list):
            print(f"❌ LLM response did not contain a 'dialog' list. Raw response: {response.choices[0].message.content}")
            raise ValueError("Invalid JSON structure from LLM")
            
        return turns_list

    except (json.JSONDecodeError, ValueError) as e:
        print(f"❌ Error processing LLM response: {e}")
        print(f"Raw LLM response: {response.choices[0].message.content}")
        raise


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
        # Use the theme from the job to generate the dialog
        turns  = [Turn(**t) for t in make_dialog(job.prompt, job.character_theme)]
        title = make_title(job.prompt)
        out_msg = DialogJob(
            job_id=job.job_id,
            title=title,
            turns=turns,
            character_theme=job.character_theme # Pass theme to the next service
        ).model_dump_json()


        ch.basic_publish(
            exchange="",
            routing_key=VIDEO_QUEUE,
            body=out_msg,
            properties=pika.BasicProperties(delivery_mode=2)
        )
        ch.basic_ack(delivery_tag=method.delivery_tag)
        print(f"[✓] Generated '{job.character_theme}' script for {job.job_id}")
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
