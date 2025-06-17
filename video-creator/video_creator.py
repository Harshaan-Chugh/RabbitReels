import os
import tempfile
import requests
# import openai                                           # type: ignore
import pika                                             # type: ignore
import numpy as np                                      # type: ignore
from PIL import Image, ImageDraw                        # type: ignore
from moviepy.editor import VideoClip, AudioFileClip     # type: ignore
from common.schemas import ScriptJob, RenderJob
from config import (
    RABBIT_URL, VIDEO_QUEUE, PUBLISH_QUEUE, VIDEO_OUT_DIR,
    ELEVEN_API_KEY, BRIAN_VOICE_ID
)

# ElevenLabs key
HEADERS = {"xi-api-key": ELEVEN_API_KEY}


def tts_to_file(text: str, wav_path: str) -> None:
    """Call ElevenLabs TTS and save a .wav file."""
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{BRIAN_VOICE_ID}"
    data = {
        "text": text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {"stability": 0.45, "similarity_boost": 0.8}
    }
    resp = requests.post(url, headers=HEADERS, json=data, stream=True, timeout=60)
    resp.raise_for_status()
    with open(wav_path, "wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            f.write(chunk)


def make_game_frame(t, size=(1080, 1920)):
    """
    Draw a simple endless-runner frame:
    - bouncing ball in center
    - scrolling platforms at bottom
    """
    W, H = size
    img = Image.new("RGB", (W, H), color=(25, 25, 25))
    draw = ImageDraw.Draw(img)

    # bouncing ball
    y = H/2 + (H/4) * np.sin(2 * np.pi * 0.5 * t)
    r = 80
    draw.ellipse(
        (W/2 - r, y - r, W/2 + r, y + r),
        fill=(230, 50, 50)
    )

    # scrolling platforms
    speed = 300  # px/sec
    spacing = 900
    for i in range(-1, 4):
        x = (speed * t + i * spacing) % (W + spacing) - spacing
        draw.rectangle(
            (x, H - 180, x + 600, H - 120),
            fill=(50, 200, 80)
        )

    return np.array(img)


def render_video(job: ScriptJob) -> str:
    """
    1) TTS → WAV
    2) Procedural VideoClip → same duration
    3) Combine audio + clip, write MP4
    """
    os.makedirs(VIDEO_OUT_DIR, exist_ok=True)
    out_mp4 = os.path.join(VIDEO_OUT_DIR, f"{job.job_id}.mp4")

    with tempfile.TemporaryDirectory() as tmp:
        wav_path = os.path.join(tmp, "speech.wav")

        # 1) Generate the TTS audio
        print("[→] Generating TTS…", flush=True)
        tts_to_file(job.script, wav_path)

        # 2) Load audio and get duration
        audioclip = AudioFileClip(wav_path)
        duration = audioclip.duration

        # 3) Create a VideoClip from our procedural function
        print("[→] Generating procedural gameplay…", flush=True)
        video_clip = VideoClip(
            make_game_frame,
            duration=duration
        ).set_fps(24)

        # 4) Attach the audio track
        final_clip = video_clip.set_audio(audioclip)

        # 5) Write the combined MP4
        print("[→] Rendering final MP4…", flush=True)
        final_clip.write_videofile(
            out_mp4,
            codec="libx264",
            audio_codec="aac",
            bitrate="4000k",
            threads=4,
            verbose=False,
            logger=None
        )

    return out_mp4


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
        print(f"[✓] Rendered video for {job.job_id}", flush=True)

    except Exception as e:
        print(f"[✗] Rendering failed for {job.job_id}: {e}", flush=True)
        ch.basic_nack(method.delivery_tag, requeue=False)


def main():
    conn = pika.BlockingConnection(pika.URLParameters(RABBIT_URL))
    ch   = conn.channel()
    ch.queue_declare(queue=VIDEO_QUEUE, durable=True)
    ch.queue_declare(queue=PUBLISH_QUEUE, durable=True)
    ch.basic_qos(prefetch_count=1)
    ch.basic_consume(queue=VIDEO_QUEUE, on_message_callback=on_message)

    print("🚀 Video Creator waiting for scripts…", flush=True)
    ch.start_consuming()


if __name__ == "__main__":
    main()
