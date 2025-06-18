import os
import glob
import json
import tempfile
import requests
import numpy as np # type: ignore
import pika # type: ignore
from moviepy.editor import ( # type: ignore
    VideoFileClip,
    AudioFileClip,
    CompositeAudioClip,
    concatenate_audioclips,
    ImageClip,
    CompositeVideoClip,
)
from moviepy.audio.fx.all import audio_loop   # type: ignore
from common.schemas import DialogJob, RenderJob
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

# ------------------------------------------------------------------------
#  constants / helpers
# ------------------------------------------------------------------------

HEADERS = {"xi-api-key": ELEVEN_API_KEY, "Accept": "audio/wav"}

VOICE_MAP  = {"peter": PETER_VOICE_ID,  "stewie": STEWIE_VOICE_ID}
IMG_MAP    = {"peter": "peter_griffin.png", "stewie": "stewie_griffin.png"}
BOUNCE_MAP = {"peter": 40, "stewie": 55}


def tts_to_file(text: str, voice_id: str, dst: str) -> None:
    """Call ElevenLabs TTS API and save the result to a file."""
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    data = {
        "text": text,
        "model_id": "eleven_monolingual_v1",
        "voice_settings": {"stability": 0.5, "similarity_boost": 0.8}
    }
    
    response = requests.post(url, json=data, headers=HEADERS)
    response.raise_for_status()
    
    with open(dst, "wb") as f:
        f.write(response.content)


def compute_rms(audio_clip: AudioFileClip, fps: int) -> list[float]:
    """Compute RMS envelope for audio clip to drive character animation."""
    try:
        # Get the audio array from the clip
        audio_array = audio_clip.to_soundarray(fps=fps)
        
        # Handle mono/stereo - convert to mono for RMS calculation
        if len(audio_array.shape) == 2:
            # Stereo - average the channels
            mono_audio = np.mean(audio_array, axis=1)
        else:
            # Already mono
            mono_audio = audio_array
        
        # Compute RMS in small windows
        window_size = int(fps * 0.05)  # 50ms windows
        rms_values = []
        
        for i in range(0, len(mono_audio), window_size):
            window = mono_audio[i:i+window_size]
            if len(window) > 0:
                rms = np.sqrt(np.mean(window**2))
                rms_values.append(float(rms))
        
        # Normalize to 0-1 range
        if rms_values:
            max_rms = max(rms_values)
            if max_rms > 0:
                rms_values = [x / max_rms for x in rms_values]
        
        return rms_values
    
    except Exception as e:
        print(f"Error computing RMS: {e}")
        # Return a flat envelope as fallback
        duration_frames = int(audio_clip.duration * fps / (fps * 0.05))
        return [0.3] * max(1, duration_frames)


# ------------------------------------------------------------------------
#  main renderer
# ------------------------------------------------------------------------

def render_video(job: DialogJob) -> str:
    """Render a dialog job into an MP4 file."""
    
    with tempfile.TemporaryDirectory() as tmp:
        bg = VideoFileClip(LONG_BG_VIDEO)
        fps = 24

        # ---- audio parts ------------------------------------------------
        audio_parts = []
        bobbles = []
        t_cursor = 0.0

        for idx, turn in enumerate(job.turns):
            wav_file = os.path.join(tmp, f"{idx}_{turn.speaker}.wav")
            tts_to_file(turn.text, VOICE_MAP[turn.speaker], wav_file)

            raw = AudioFileClip(wav_file)
            if raw.nchannels == 1:
                raw = raw.set_channels(2)

            env = compute_rms(raw, fps)
            clip = raw.set_start(t_cursor)
            audio_parts.append(clip)

            # ---- character bobble -------------------------------------------
            img_path = os.path.join(os.path.dirname(__file__), 'assets', IMG_MAP[turn.speaker])
            
            def make_bobble_fn(envelope, bounce_height):
                def bobble(t):
                    frame_idx = int(t * fps * 0.05)  # Match the RMS window rate
                    if frame_idx < len(envelope):
                        y_offset = int(bounce_height * envelope[frame_idx])
                        return ("center", 800 - y_offset)
                    return ("center", 800)
                return bobble

            img_clip = (ImageClip(img_path)
                        .set_duration(raw.duration)
                        .set_start(t_cursor)
                        .set_pos(make_bobble_fn(env, BOUNCE_MAP[turn.speaker])))
            bobbles.append(img_clip)

            t_cursor += raw.duration

        if not audio_parts:
            raise ValueError("No audio parts generated")

        total_dur = t_cursor
        bg = (bg.subclip(0, total_dur)
                .crop(width=1080, height=1920, x_center=bg.w/2, y_center=bg.h/2))

        # ---- narration track --------------------------------------------
        narration = CompositeAudioClip(audio_parts)

        # ---- optional music underneath ----------------------------------
        mp3s = glob.glob(os.path.join(AUDIO_ASSETS_DIR, "*.mp3"))
        if mp3s:
            music = AudioFileClip(mp3s[0])
            music = audio_loop(music, duration=total_dur).volumex(0.1)
            final_audio = CompositeAudioClip([narration, music])
        else:
            final_audio = narration

        # ---- compose & export -------------------------------------------
        video = CompositeVideoClip([bg] + bobbles).set_audio(final_audio)
        
        os.makedirs(VIDEO_OUT_DIR, exist_ok=True)
        out_path = os.path.join(VIDEO_OUT_DIR, f"{job.job_id}.mp4")
        
        video.write_videofile(out_path, fps=fps, codec='libx264', audio_codec='aac')
        
        # Clean up
        video.close()
        bg.close()
        for clip in audio_parts:
            clip.close()
        for clip in bobbles:
            clip.close()
        
        return out_path


# ------------------------------------------------------------------------
#  RabbitMQ plumbing
# ------------------------------------------------------------------------

def on_message(ch, method, props, body):
    try:
        job = DialogJob.model_validate_json(body)
        print(f"🎬 Rendering video for {job.job_id}...")
        
        video_path = render_video(job)
        
        # Send to publish queue
        render_job = RenderJob(job_id=job.job_id, title=job.title, storage_path=video_path)
        
        connection = pika.BlockingConnection(pika.URLParameters(RABBIT_URL))
        channel = connection.channel()
        channel.queue_declare(queue=PUBLISH_QUEUE, durable=True)
        channel.basic_publish(
            exchange='',
            routing_key=PUBLISH_QUEUE,
            body=render_job.model_dump_json(),
            properties=pika.BasicProperties(delivery_mode=2)
        )
        connection.close()
        
        print(f"✅ Video rendered: {video_path}")
        ch.basic_ack(delivery_tag=method.delivery_tag)
        
    except Exception as e:
        print(f"[✗] Rendering failed for {getattr(job, 'job_id', 'unknown')}: {e}")
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)


def main():
    connection = pika.BlockingConnection(pika.URLParameters(RABBIT_URL))
    channel = connection.channel()
    channel.queue_declare(queue=VIDEO_QUEUE, durable=True)
    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue=VIDEO_QUEUE, on_message_callback=on_message)
    
    print("🚀 Video Creator waiting for scripts…")
    channel.start_consuming()


if __name__ == "__main__":
    main()
