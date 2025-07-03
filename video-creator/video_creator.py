# 3rd-party
import os, glob, json, tempfile, base64, re, random, time, traceback
import requests, numpy as np            # type: ignore
import pika                             # type: ignore
import redis                            # type: ignore
from typing import List, Dict, Tuple
from requests.exceptions import ConnectionError, Timeout, HTTPError
import socket
from moviepy.editor import (            # type: ignore
    VideoFileClip,
    AudioFileClip,
    CompositeAudioClip,
    TextClip,          # NEW – captions
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
    RICK_VOICE_ID,
    MORTY_VOICE_ID,
    LONG_BG_VIDEO,
    AUDIO_ASSETS_DIR,
    REDIS_URL,
    ENABLE_PUBLISHER,
    TTS_MAX_RETRIES,
    TTS_RETRY_DELAY,
    TTS_BACKOFF_MULTIPLIER,
    DATABASE_URL,
)

# ElevenLabs API headers
HEADERS = {"xi-api-key": ELEVEN_API_KEY}

# --- NEW: Generalized Character Asset Configuration ---
CHARACTER_ASSETS = {
    "family_guy": {
        "peter": {"voice_id": PETER_VOICE_ID, "image": "peter_griffin.png"},
        "stewie": {"voice_id": STEWIE_VOICE_ID, "image": "stewie_griffin.png"}
    },    "rick_and_morty": {
        "rick": {"voice_id": RICK_VOICE_ID, "image": "rick.png"},
        "morty": {"voice_id": MORTY_VOICE_ID, "image": "morty.png"}
    }
}
CHAR_HEIGHT = 650

# ── TTS API Retry Configuration ────────────────────────────────────────────────
# Use imported config values

def tts_api_call_with_retry(url: str, payload: dict, headers: dict, max_retries: int = TTS_MAX_RETRIES) -> requests.Response:
    """
    Make a TTS API call with retry logic for handling transient network errors.
    Retries on connection errors, timeouts, socket errors (including ConnectionResetError), and 5xx server errors.
    """
    last_exception = None
    
    for attempt in range(max_retries + 1):
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            response.raise_for_status()
            return response
        except HTTPError as e:
            # HTTP errors - only retry on 5xx server errors
            if e.response.status_code >= 500:
                last_exception = e
                if attempt < max_retries:
                    delay = TTS_RETRY_DELAY * (TTS_BACKOFF_MULTIPLIER ** attempt)
                    print(f"TTS API server error (attempt {attempt + 1}/{max_retries + 1}): HTTP {e.response.status_code}")
                    print(f"Retrying in {delay} seconds...")
                    time.sleep(delay)
                else:
                    print(f"TTS API server error after {max_retries + 1} attempts: HTTP {e.response.status_code}")
            else:
                # 4xx client errors - don't retry
                print(f"TTS API client error (not retrying): HTTP {e.response.status_code}")
                raise
        except (ConnectionError, Timeout, socket.error, OSError) as e:
            # Network-level errors including ConnectionResetError - retry
            last_exception = e
            if attempt < max_retries:
                delay = TTS_RETRY_DELAY * (TTS_BACKOFF_MULTIPLIER ** attempt)
                print(f"TTS API network error (attempt {attempt + 1}/{max_retries + 1}): {type(e).__name__}: {e}")
                print(f"Retrying in {delay} seconds...")
                time.sleep(delay)
            else:
                print(f"TTS API network error after {max_retries + 1} attempts: {type(e).__name__}: {e}")
        except Exception as e:
            # Other unexpected errors - don't retry
            print(f"TTS API unexpected error (not retrying): {type(e).__name__}: {e}")
            raise
    
    # If we get here, all retries failed
    if last_exception:
        raise last_exception
    else:
        raise Exception("TTS API call failed after all retries")

# ── caption style ────────────────────────────────────────────────────────────
# Thick, punchy subtitles for Shorts
FONT        = "DejaVu-Sans-Bold"   
FONTSIZE    = 75                    # Reduced from 100 for smaller size
STROKE      = 3                     # Increased stroke for more boldness
# caption block is centred horizontally and sits CAP_Y_BASE px above bottom
CAP_Y_BASE  = 1300                 # Changed from 1120 to 1300 (moves text higher up)
# layout limits
MAX_LINE_W   = 920                
LINE_SPACING = 20                 

def tts_to_file(text: str, voice_id: str, dst: str) -> None:
    """
    Call ElevenLabs TTS API and save the result to a file with retry logic.
    """
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    payload = {
        "text": text,
        "model_id": "eleven_monolingual_v1",
        "voice_settings": {"stability": 0.5, "similarity_boost": 0.8}
    }
    
    try:
        response = tts_api_call_with_retry(url, payload, HEADERS)
        with open(dst, "wb") as f:
            f.write(response.content)
    except Exception as e:
        print(f"Failed to generate TTS for text: {text[:50]}...")
        print(f"Error: {e}")
        raise

def tts_with_timestamps(text: str, voice_id: str, tmp_dir: str) -> tuple[str, list[dict]]:
    """
    Generate TTS with word-level timestamps using retry logic.
    """
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/with-timestamps"
    payload = {
        "text": text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.8,
            "style": 0.0,
            "use_speaker_boost": True
        }
    }
    
    try:
        response = tts_api_call_with_retry(url, payload, HEADERS)
        result = response.json()
    except Exception as e:
        print(f"Failed to generate TTS with timestamps for text: {text[:50]}...")
        print(f"Error: {e}")
        raise

    if "audio_base64" in result and "alignment" in result:
        audio_data = base64.b64decode(result["audio_base64"])
        wav_file = os.path.join(tmp_dir, f"{hash(text)}.wav")
        with open(wav_file, "wb") as f:
            f.write(audio_data)

        # Assemble word timings
        word_timings = []
        if ("characters" in result["alignment"]
            and "character_start_times_seconds" in result["alignment"]
            and "character_end_times_seconds" in result["alignment"]):

            chars     = result["alignment"]["characters"]
            starts    = result["alignment"]["character_start_times_seconds"]
            ends      = result["alignment"]["character_end_times_seconds"]
            curr_word = ""
            w_start   = None

            for i, ch in enumerate(chars):
                if ch.isspace():
                    if curr_word:
                        word_timings.append({
                            "word": curr_word,
                            "start": w_start,
                            "end": ends[i-1]
                        })
                        curr_word = ""
                        w_start   = None
                else:
                    if w_start is None:
                        w_start = starts[i]
                    curr_word += ch

            if curr_word:
                word_timings.append({
                    "word": curr_word,
                    "start": w_start,
                    "end": ends[-1]
                })
        return wav_file, word_timings

    raise requests.exceptions.HTTPError("No timestamp data available")

def build_caption_layers(sentence: str,
                         word_times: List[Dict],
                         t_start: float) -> List[TextClip]:
    """
    Build subtitles that show one line at a time with karaoke highlighting.
    Lines replace each other in the same position.
    """
    global FONT
    try:
        TextClip("T", font=FONT, fontsize=FONTSIZE).close()
    except Exception:
        FONT = "DejaVu-Sans-Bold"

    if not word_times:
        return []

    # Configuration for line breaking - FURTHER REDUCED to prevent overflow
    MAX_CHARS_PER_LINE = 25  # Reduced from 28 to 25
    WORDS_PER_LINE = 3       # Reduced from 4 to 3 words max per line
    
    # Split sentence into lines based on word count/length
    words = sentence.split()
    lines = []
    current_line = []
    current_length = 0
    
    for word in words:
        word_length = len(word) + 1  # +1 for space
        if (current_length + word_length > MAX_CHARS_PER_LINE or 
            len(current_line) >= WORDS_PER_LINE) and current_line:
            # Start a new line
            lines.append(current_line.copy())
            current_line = [word]
            current_length = len(word)
        else:
            current_line.append(word)
            current_length += word_length
    
    # Add the last line
    if current_line:
        lines.append(current_line)
    
    if not lines:
        return []

    clips = []
    word_index = 0
    
    caption_y = 1920 - CAP_Y_BASE
    
    for line_num, line_words in enumerate(lines):
        line_word_times = []
        line_start_time = None
        line_end_time = None
        
        for line_word in line_words:
            clean_line_word = re.sub(r'[^\w\']', '', line_word.lower())
            
            found_match = False
            for i in range(word_index, len(word_times)):
                clean_tts_word = re.sub(r'[^\w\']', '', word_times[i]["word"].lower())
                if clean_tts_word == clean_line_word:
                    word_timing = word_times[i]
                    line_word_times.append({
                        "word": line_word,
                        "start": word_timing["start"],
                        "end": word_timing["end"]
                    })
                    
                    if line_start_time is None:
                        line_start_time = word_timing["start"]
                    line_end_time = word_timing["end"]
                    
                    word_index = i + 1
                    found_match = True
                    break
            
            if not found_match:
                print(f"⚠️ Could not find timing for word: '{line_word}'")
        
        if not line_word_times or line_start_time is None:
            continue
        
        line_text = ' '.join(line_words)
        line_duration = line_end_time - line_start_time
        
        print(f"📝 Line {line_num + 1}: '{line_text}' from {line_start_time:.1f}s to {line_end_time:.1f}s at y={caption_y}")
        
        word_clips_info = []
        total_width = 0
        
        for word_data in line_word_times:
            word_clip = TextClip(word_data["word"], font=FONT, fontsize=FONTSIZE, method="label")
            word_clips_info.append({
                "word_data": word_data,
                "width": word_clip.w
            })
            total_width += word_clip.w
            word_clip.close()
        
        if len(word_clips_info) > 1:
            space_clip = TextClip(" ", font=FONT, fontsize=FONTSIZE)
            space_width = space_clip.w
            total_width += space_width * (len(word_clips_info) - 1)
            space_clip.close()
        else:
            space_width = 0
        
        max_width = 900
        if total_width > max_width:
            print(f"⚠️ Line too wide ({total_width}px), will be clipped to {max_width}px")
        
        line_start_x = (1080 - total_width) // 2
        
        line_start_x = max(40, min(line_start_x, 1040 - total_width))
        
        print(f"📐 Line width: {total_width}px, start_x: {line_start_x}")
        
        current_x = line_start_x
        
        for i, word_info in enumerate(word_clips_info):
            word_data = word_info["word_data"]
            word_text = word_data["word"]
            word_start = word_data["start"]
            word_end = word_data["end"]
            
            try:
                white_word = (TextClip(word_text, 
                                     font=FONT, 
                                     fontsize=FONTSIZE,
                                     color="white",
                                     stroke_width=STROKE, 
                                     stroke_color="black",
                                     method="label")
                            .set_start(t_start + line_start_time)
                            .set_duration(line_duration)
                            .set_position((current_x, caption_y)))
                
                clips.append(white_word)
                
                yellow_word = (TextClip(word_text, 
                                      font=FONT, 
                                      fontsize=FONTSIZE,
                                      color="yellow",
                                      stroke_width=STROKE, 
                                      stroke_color="black",
                                      method="label")
                             .set_start(t_start + word_start)
                             .set_duration(word_end - word_start)
                             .set_position((current_x, caption_y)))
                
                clips.append(yellow_word)
                
                current_x += word_info["width"]
                if i < len(word_clips_info) - 1:
                    current_x += space_width
                
                print(f"  📍 '{word_text}' at x={current_x - word_info['width']}")
                
            except Exception as e:
                print(f"❌ Error creating word clips for '{word_text}': {e}")

    print(f"✓ Created {len(clips)} caption clips for {len(lines)} lines")
    return clips

def render_video(job: DialogJob) -> str:
    """
    Render a dialog job into an MP4 file.
    """
    try:
        r = redis.from_url(REDIS_URL, decode_responses=True)
    except Exception as e:
        print(f"Warning: Redis connection failed, continuing without progress updates: {e}")
        r = None
    
    def update_progress(progress: float, stage: str = ""):
        """
        Update rendering progress in Redis
        """
        if r:
            try:
                status_data = {
                    "job_id": job.job_id,
                    "status": "rendering",
                    "progress": progress,
                    "stage": stage
                }
                r.set(job.job_id, json.dumps(status_data))
                print(f"Progress: {progress:.1%} - {stage}")
            except Exception as e:
                print(f"Warning: Failed to update progress: {e}")
    
    asset_map = CHARACTER_ASSETS.get(job.character_theme)
    if not asset_map:
        raise ValueError(f"No assets found for theme: {job.character_theme}")

    update_progress(0.15, "Initializing video rendering")

    with tempfile.TemporaryDirectory() as tmp:
        bg       = VideoFileClip(LONG_BG_VIDEO)
        fps      = 24
        t_cursor = 0.0
        audio_parts = []
        visuals     = []

        total_turns = len(job.turns)
        update_progress(0.2, f"Processing {total_turns} dialog turns")

        for i, turn in enumerate(job.turns):
            speaker_assets = None
            for key, assets in asset_map.items():
                if key.lower() == turn.speaker.lower():
                    speaker_assets = assets
                    break
            
            if not speaker_assets:
                available_speakers = list(asset_map.keys())
                raise ValueError(f"Assets for speaker '{turn.speaker}' not found in theme '{job.character_theme}'. Available speakers: {available_speakers}")
            
            turn_progress = 0.2 + (i / total_turns) * 0.5
            update_progress(turn_progress, f"Generating speech for {turn.speaker} (turn {i+1}/{total_turns})")
            
            try:
                wav, wts = tts_with_timestamps(turn.text, speaker_assets["voice_id"], tmp)
            except requests.exceptions.HTTPError as e:
                print(f"TTS with timestamps failed for {turn.speaker}, falling back to basic TTS: {e}")
                wav = os.path.join(tmp, f"{hash(turn.text)}.wav")
                try:
                    tts_to_file(turn.text, speaker_assets["voice_id"], wav)
                    dur = AudioFileClip(wav).duration
                    wts = [{"word": turn.text, "start": 0.0, "end": dur}]
                except Exception as tts_e:
                    raise Exception(f"TTS generation failed for {turn.speaker}: {tts_e}") from tts_e
            except Exception as e:
                raise Exception(f"TTS processing failed for {turn.speaker}: {e}") from e

            raw = AudioFileClip(wav)
            if raw.nchannels == 1:
                raw = raw.set_channels(2)
            
            if turn.speaker.lower() in ['stewie', 'morty']:
                raw = raw.volumex(1.25)
                print(f"🔊 Amplified {turn.speaker}'s voice by 25%")
            
            clip = raw.set_start(t_cursor)
            audio_parts.append(clip)

            img_path = os.path.join(os.path.dirname(__file__), "assets", speaker_assets["image"])
            
            sprite = (
                ImageClip(img_path)
                .resize(height=CHAR_HEIGHT)
                .set_duration(raw.duration)
                .set_start(t_cursor)
                .set_position((30, 1920-CHAR_HEIGHT-150))
            )
            visuals.append(sprite)
            
            print(f"🐰 Added {turn.speaker} static sprite: start={t_cursor:.1f}s, duration={raw.duration:.1f}s")

            caps = build_caption_layers(turn.text, wts, t_cursor)
            visuals.extend(caps)

            t_cursor += raw.duration

        if not audio_parts:
            raise ValueError("No audio to render")

        update_progress(0.75, "Compositing video and audio")
        total = t_cursor
        mstart = max(0, bg.duration - total - 5)
        rs = 0 if mstart <= 0 else random.uniform(0, mstart)
        bg = (
            bg.subclip(rs, rs + total)
              .crop(width=1080, height=1920, x_center=bg.w/2, y_center=bg.h/2)
        )

        narration = CompositeAudioClip(audio_parts)
        mp3s = glob.glob(os.path.join(AUDIO_ASSETS_DIR, "*.mp3"))
        if mp3s:
            music = audio_loop(AudioFileClip(mp3s[0]), duration=total).volumex(0.1)
            final_audio = CompositeAudioClip([narration, music])
        else:
            final_audio = narration

        video = CompositeVideoClip([bg] + visuals).set_audio(final_audio)
        os.makedirs(VIDEO_OUT_DIR, exist_ok=True)
        out = os.path.join(VIDEO_OUT_DIR, f"{job.job_id}.mp4")
        
        video.write_videofile(
            out, 
            fps=fps, 
            codec="libx264",
            audio_codec="aac",
            temp_audiofile="temp-audio.m4a",
            remove_temp=True,
            preset="medium",
            ffmpeg_params=[
                "-movflags", "+faststart",  # Enable fast start for web streaming
                "-pix_fmt", "yuv420p",      # Ensure compatibility with all players
                "-crf", "23",               # Good quality balance
                "-maxrate", "5M",           # Limit bitrate for file size
                "-bufsize", "10M"           # Buffer size
            ]
        )

        video.close(); bg.close()
        for c in audio_parts: c.close()
        for c in visuals:     c.close()
        return out

def increment_video_count_postgres():
    try:
        api_url = "http://api:8080/api/video-count/increment"
        response = requests.post(api_url)
        if response.ok:
            result = response.json()
            count = result.get('count', 'unknown')
            print(f"📊 Global video count incremented to {count} in Postgres.")
        else:
            print(f"⚠️ Failed to increment video count in Postgres: {response.status_code} {response.text}")
    except Exception as e:
        print(f"⚠️ Error incrementing video count in Postgres: {e}")

def on_message(ch, method, props, body):
    job = DialogJob.model_validate_json(body)
    video_generation_successful = False
    video_path = None
    
    try:
        print(f"🐰 Rendering video for {job.job_id}…")
        
        try:
            r = redis.from_url(REDIS_URL, decode_responses=True)
            status_data = {
                "job_id": job.job_id,
                "status": "rendering",
                "progress": 0.1
            }
            r.set(job.job_id, json.dumps(status_data))
            print(f"Updated Redis status to 'rendering' for {job.job_id}")
        except Exception as e:
            print(f"Warning: Failed to update Redis status to rendering: {e}")
        
        video_path = render_video(job)
        
        if not os.path.exists(video_path) or os.path.getsize(video_path) < 1000:
            raise Exception("Video file not created properly or is too small")
        
        try:
            r = redis.from_url(REDIS_URL, decode_responses=True)
            status_data = {
                "job_id": job.job_id,
                "status": "done",
                "download_url": f"/videos/{job.job_id}/file"
            }
            r.set(job.job_id, json.dumps(status_data))
            print(f"Updated Redis status to 'done' for {job.job_id}")
        except Exception as e:
            print(f"Error updating Redis status to done: {e}")
            raise Exception(f"Video created but failed to update status: {str(e)}")
        
        video_generation_successful = True
        print(f"✅ Video successfully created: {video_path}")
        
        increment_video_count_postgres()
        
    except Exception as e:
        print(f"[✗] Video generation failed for {job.job_id}: {e}")
        
        try:
            r = redis.from_url(REDIS_URL, decode_responses=True)
            error_status = {
                "job_id": job.job_id,
                "status": "error",
                "error_msg": f"Video generation failed: {str(e)}"
            }
            r.set(job.job_id, json.dumps(error_status))
            print(f"Updated Redis status to 'error' for {job.job_id}")
        except Exception as redis_e:
            print(f"Warning: Failed to update Redis error status: {redis_e}")
    
    if video_generation_successful and video_path:
        try:
            msg = RenderJob(job_id=job.job_id,
                           title=job.title,
                           storage_path=video_path).model_dump_json()
            
            if ENABLE_PUBLISHER:
                try:
                    if not RABBIT_URL:
                        raise ValueError("RABBIT_URL is not configured")
                    conn = pika.BlockingConnection(pika.URLParameters(RABBIT_URL))
                    chan = conn.channel()
                    chan.queue_declare(queue=PUBLISH_QUEUE, durable=True)
                    chan.basic_publish(exchange="", routing_key=PUBLISH_QUEUE,
                                      body=msg,
                                      properties=pika.BasicProperties(delivery_mode=2))
                    conn.close()
                    print(f"✅ Video published to publisher queue: {video_path}")
                except Exception as pub_e:
                    print(f"⚠️ Publisher queue failed (video already completed): {pub_e}")
            else:
                print(f"✅ Video ready (publisher disabled): {video_path}")
        except Exception as post_e:
            print(f"⚠️ Post-processing failed (video already completed): {post_e}")

def main():
    while True:
        try:
            if not RABBIT_URL:
                raise ValueError("RABBIT_URL is not configured")
            connection_params = pika.URLParameters(RABBIT_URL)
            connection_params.heartbeat = 30
            connection_params.blocked_connection_timeout = 300
            connection_params.connection_attempts = 3
            connection_params.retry_delay = 2
            
            conn = pika.BlockingConnection(connection_params)
            ch = conn.channel()
            ch.queue_declare(queue=VIDEO_QUEUE, durable=True)
            ch.basic_qos(prefetch_count=1)
            ch.basic_consume(queue=VIDEO_QUEUE, on_message_callback=on_message, auto_ack=True)
            print("🚀 Video Creator waiting for scripts…")
            ch.start_consuming()
        except KeyboardInterrupt:
            print("🛑 Video Creator shutting down...")
            if 'ch' in locals():
                ch.stop_consuming()
            if 'conn' in locals():
                conn.close()
            break
        except Exception as e:
            print(f"⚠️ Connection error: {e}. Reconnecting in 5 seconds...")
            import time
            time.sleep(5)

if __name__ == "__main__":
    main()
