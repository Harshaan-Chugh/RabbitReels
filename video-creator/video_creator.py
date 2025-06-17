import os
import tempfile
import requests
import random
import glob
import wave
import numpy as np  # type: ignore
import pika                                  # type: ignore
from moviepy.editor import (
    VideoFileClip,
    AudioFileClip,
    CompositeAudioClip,
    ImageClip,
    CompositeVideoClip,
)
from moviepy.audio.fx.all import audio_loop   # type: ignore
from common.schemas import ScriptJob, RenderJob
from config import (
    RABBIT_URL,
    VIDEO_QUEUE,
    PUBLISH_QUEUE,
    VIDEO_OUT_DIR,
    ELEVEN_API_KEY,
    PETER_VOICE_ID,
    STEWIE_VOICE_ID,
    LONG_BG_VIDEO,
    AUDIO_ASSETS_DIR,
)

# ElevenLabs key header + request WAV
HEADERS = {
    "xi-api-key": ELEVEN_API_KEY,
    "Accept": "audio/wav"
}

def tts_to_file(text: str, wav_path: str) -> None:
    """Call ElevenLabs TTS and save a proper .wav file."""
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{PETER_VOICE_ID}"
    data = {
        "text": text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {"stability": 0.45, "similarity_boost": 0.8},
        "output_format": "wav"
    }
    resp = requests.post(url, headers=HEADERS, json=data, stream=True, timeout=60)
    resp.raise_for_status()
    with open(wav_path, "wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            f.write(chunk)


def render_video(job: ScriptJob) -> str:
    os.makedirs(VIDEO_OUT_DIR, exist_ok=True)
    out_mp4 = os.path.join(VIDEO_OUT_DIR, f"{job.job_id}.mp4")

    with tempfile.TemporaryDirectory() as tmp:
        wav_path = os.path.join(tmp, "speech.wav")

        # 1) TTS → WAV
        print("[→] Generating TTS…", flush=True)
        tts_to_file(job.script, wav_path)

        # 2) Load audio and stereo-ify if needed
        tts_audio = AudioFileClip(wav_path)
        if tts_audio.nchannels == 1:
            tts_audio = tts_audio.set_channels(2)
        duration = tts_audio.duration
        fps = 24

        # 3) Pick a random subclip from the background
        print("[→] Loading long background…", flush=True)
        bg = VideoFileClip(LONG_BG_VIDEO)
        start = random.uniform(0, max(0, bg.duration - duration))
        clip = bg.subclip(start, start + duration)

        # 4) Center-crop to 1080×1920
        clip = clip.crop(
            width=1080,
            height=1920,
            x_center=clip.w / 2,
            y_center=clip.h / 2,
        )

        # 5) Transcode TTS → real PCM-WAV then compute RMS per video frame
        pcm_wav = os.path.join(tmp, "speech_pcm.wav")
        tts_audio.write_audiofile(
            pcm_wav,
            fps=44100,
            nbytes=2,
            codec="pcm_s16le",
            verbose=False, logger=None
        )

        with wave.open(pcm_wav, "rb") as w:
            sr        = w.getframerate()
            n_ch      = w.getnchannels()
            n_frames  = w.getnframes()
            raw       = w.readframes(n_frames)

        samples = np.frombuffer(raw, dtype=np.int16).astype(np.float32)
        if n_ch == 2:
            samples = samples.reshape(-1, 2).mean(axis=1)
        samples /= np.abs(samples).max() or 1.0

        samples_per_f = int(sr / fps)
        total_frames  = int(duration * fps)
        rms_by_frame  = [
            np.sqrt(np.mean(np.square(
                samples[i*samples_per_f:(i+1)*samples_per_f]
            ))) for i in range(total_frames)
        ]
        peak = max(rms_by_frame) or 1.0
        rms_by_frame = [r/peak for r in rms_by_frame]

        # 6) Optional MP3 background
        print("[→] Loading background tracks…", flush=True)
        mp3s = glob.glob(os.path.join(AUDIO_ASSETS_DIR, "*.mp3"))
        if mp3s:
            track = random.choice(mp3s)
            bg_audio = audio_loop(AudioFileClip(track), duration=duration).volumex(0.65)
            final_audio = CompositeAudioClip([bg_audio, tts_audio])
        else:
            final_audio = tts_audio

        # 7) Bobble-head
        bobble = (
            ImageClip(os.path.join(AUDIO_ASSETS_DIR, "peter_griffin.png"))
            .set_duration(duration)
            .resize(height=450)
        )
        base_x = 30
        base_y = 1920 - bobble.h - 225
        max_bounce = 40

        def bobble_pos(t):
            idx = min(int(t * fps), len(rms_by_frame) - 1)
            return (base_x, base_y - rms_by_frame[idx] * max_bounce)

        bobble = bobble.set_position(bobble_pos)

        # 8) Composite and attach audio
        final_clip = CompositeVideoClip([clip, bobble]).set_audio(final_audio)

        # 9) Export
        print("[→] Rendering final MP4…", flush=True)
        final_clip.write_videofile(
            out_mp4,
            codec="libx264",
            audio_codec="aac",
            bitrate="4000k",
            threads=4,
            fps=fps,
            verbose=False,
            logger=None,
        )

    return out_mp4


def on_message(ch, method, props, body):
    job = ScriptJob.model_validate_json(body)
    try:
        video_path = render_video(job)
        msg = RenderJob(
            job_id=job.job_id,
            title=job.title,
            storage_path=video_path,
        ).model_dump_json()
        ch.basic_publish(
            exchange="",
            routing_key=PUBLISH_QUEUE,
            body=msg,
            properties=pika.BasicProperties(delivery_mode=2),
        )
        ch.basic_ack(delivery_tag=method.delivery_tag)
        print(f"[✓] Rendered video for {job.job_id}", flush=True)
    except Exception as e:
        print(f"[✗] Rendering failed for {job.job_id}: {e}", flush=True)
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)


def main():
    conn = pika.BlockingConnection(pika.URLParameters(RABBIT_URL))
    ch = conn.channel()
    ch.queue_declare(queue=VIDEO_QUEUE, durable=True)
    ch.queue_declare(queue=PUBLISH_QUEUE, durable=True)
    ch.basic_qos(prefetch_count=1)
    ch.basic_consume(queue=VIDEO_QUEUE, on_message_callback=on_message)

    print("🚀 Video Creator waiting for scripts…", flush=True)
    ch.start_consuming()


if __name__ == "__main__":
    main()
