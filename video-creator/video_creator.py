# 3rd-party
import os, glob, json, tempfile, base64, re, random
import requests, numpy as np            # type: ignore
import pika                             # type: ignore
from typing import List, Dict, Tuple
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
    STEWIE_VOICE_ID,    RICK_VOICE_ID,
    MORTY_VOICE_ID,
    LONG_BG_VIDEO,    AUDIO_ASSETS_DIR,
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

def tts_with_timestamps(text: str, voice_id: str, tmp_dir: str) -> tuple[str, list[dict]]:
    """Generate TTS with word-level timestamps."""
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
    response = requests.post(url, json=payload, headers=HEADERS)
    response.raise_for_status()
    result = response.json()

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
    
    # FIXED: All lines appear in the SAME position (no vertical stacking)
    caption_y = 1920 - CAP_Y_BASE  # Single Y position for all lines (now higher up)
    
    # Process each line separately
    for line_num, line_words in enumerate(lines):
        # Find timing for words in this line
        line_word_times = []
        line_start_time = None
        line_end_time = None
        
        for line_word in line_words:
            # Find matching word in word_times
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
        
        # Skip this line if no timings found
        if not line_word_times or line_start_time is None:
            continue
        
        line_text = ' '.join(line_words)
        line_duration = line_end_time - line_start_time
        
        print(f"📝 Line {line_num + 1}: '{line_text}' from {line_start_time:.1f}s to {line_end_time:.1f}s at y={caption_y}")
        
        # FIXED: Better width calculation and centering
        word_clips_info = []
        total_width = 0
        
        # First pass: calculate individual word widths
        for word_data in line_word_times:
            word_clip = TextClip(word_data["word"], font=FONT, fontsize=FONTSIZE, method="label")
            word_clips_info.append({
                "word_data": word_data,
                "width": word_clip.w
            })
            total_width += word_clip.w
            word_clip.close()
        
        # Add space widths (except for last word)
        if len(word_clips_info) > 1:
            space_clip = TextClip(" ", font=FONT, fontsize=FONTSIZE)
            space_width = space_clip.w
            total_width += space_width * (len(word_clips_info) - 1)
            space_clip.close()
        else:
            space_width = 0
        
        # FIXED: More conservative width limit to prevent right edge overflow
        max_width = 900  # Reduced from 1000 to 900px (leaves 90px margin on each side)
        if total_width > max_width:
            print(f"⚠️ Line too wide ({total_width}px), will be clipped to {max_width}px")
            # Don't truncate, just warn - let it break to next line naturally
        
        # FIXED: Better centering calculation
        line_start_x = (1080 - total_width) // 2
        
        # Ensure we don't go negative or too far right
        line_start_x = max(40, min(line_start_x, 1040 - total_width))
        
        print(f"📐 Line width: {total_width}px, start_x: {line_start_x}")
        
        # Second pass: create clips with correct positions
        current_x = line_start_x
        
        for i, word_info in enumerate(word_clips_info):
            word_data = word_info["word_data"]
            word_text = word_data["word"]
            word_start = word_data["start"]
            word_end = word_data["end"]
            
            try:
                # WHITE base word (visible for entire line duration)
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
                
                # YELLOW highlight (visible only when this word is spoken)
                yellow_word = (TextClip(word_text, 
                                      font=FONT, 
                                      fontsize=FONTSIZE,
                                      color="yellow",
                                      stroke_width=STROKE, 
                                      stroke_color="black",
                                      method="label")
                             .set_start(t_start + word_start)
                             .set_duration(word_end - word_start)
                             .set_position((current_x, caption_y)))  # SAME position as white
                
                clips.append(yellow_word)
                
                # Update position for next word
                current_x += word_info["width"]
                if i < len(word_clips_info) - 1:  # Add space except for last word
                    current_x += space_width
                
                print(f"  📍 '{word_text}' at x={current_x - word_info['width']}")
                
            except Exception as e:
                print(f"❌ Error creating word clips for '{word_text}': {e}")

    print(f"✓ Created {len(clips)} caption clips for {len(lines)} lines")
    return clips

def render_video(job: DialogJob) -> str:
    """Render a dialog job into an MP4 file."""
    # Get the asset map for the current theme
    asset_map = CHARACTER_ASSETS.get(job.character_theme)
    if not asset_map:
        raise ValueError(f"No assets found for theme: {job.character_theme}")

    with tempfile.TemporaryDirectory() as tmp:
        bg       = VideoFileClip(LONG_BG_VIDEO)
        fps      = 24
        t_cursor = 0.0
        audio_parts = []
        visuals     = []

        for turn in job.turns:
            speaker_assets = asset_map.get(turn.speaker)
            if not speaker_assets:
                raise ValueError(f"Assets for speaker '{turn.speaker}' not found in theme '{job.character_theme}'")

            # TTS + timestamps (with fallback)
            try:
                # Use voice_id from the new asset map
                wav, wts = tts_with_timestamps(turn.text, speaker_assets["voice_id"], tmp)
            except requests.exceptions.HTTPError:
                wav = os.path.join(tmp, f"{hash(turn.text)}.wav")
                tts_to_file(turn.text, speaker_assets["voice_id"], wav)
                dur = AudioFileClip(wav).duration
                wts = [{"word": turn.text, "start": 0.0, "end": dur}]

            raw = AudioFileClip(wav)
            if raw.nchannels == 1:
                raw = raw.set_channels(2)
            clip = raw.set_start(t_cursor)
            audio_parts.append(clip)

            # Static character sprite (no bouncing)
            # Use image from the new asset map
            img_path = os.path.join(os.path.dirname(__file__), "assets", speaker_assets["image"])
            
            sprite = (
                ImageClip(img_path)
                .resize(height=CHAR_HEIGHT)
                .set_duration(raw.duration)
                .set_start(t_cursor)
                .set_position((30, 1920-CHAR_HEIGHT-150))  # Static position
            )
            visuals.append(sprite)
            
            print(f"🎭 Added {turn.speaker} static sprite: start={t_cursor:.1f}s, duration={raw.duration:.1f}s")

            # captions
            caps = build_caption_layers(turn.text, wts, t_cursor)
            visuals.extend(caps)

            t_cursor += raw.duration

        if not audio_parts:
            raise ValueError("No audio to render")

        total = t_cursor
        # randomize background start
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
        video.write_videofile(out, fps=fps, codec="libx264", audio_codec="aac")

        # cleanup
        video.close(); bg.close()
        for c in audio_parts: c.close()
        for c in visuals:     c.close()
        return out

def on_message(ch, method, props, body):
    job = DialogJob.model_validate_json(body)
    try:
        print(f"🎬 Rendering video for {job.job_id}…")
        path = render_video(job)
        msg  = RenderJob(job_id=job.job_id,
                         title=job.title,
                         storage_path=path).model_dump_json()
        conn = pika.BlockingConnection(pika.URLParameters(RABBIT_URL))
        chan = conn.channel()
        chan.queue_declare(queue=PUBLISH_QUEUE, durable=True)
        chan.basic_publish(exchange="", routing_key=PUBLISH_QUEUE,
                          body=msg,
                          properties=pika.BasicProperties(delivery_mode=2))
        conn.close()
        ch.basic_ack(delivery_tag=method.delivery_tag)
        print(f"✅ Video published: {path}")
    except Exception as e:
        print(f"[✗] Rendering failed for {job.job_id}: {e}")
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

def main():
    conn = pika.BlockingConnection(pika.URLParameters(RABBIT_URL))
    ch   = conn.channel()
    ch.queue_declare(queue=VIDEO_QUEUE, durable=True)
    ch.basic_qos(prefetch_count=1)
    ch.basic_consume(queue=VIDEO_QUEUE, on_message_callback=on_message)
    print("🚀 Video Creator waiting for scripts…")
    ch.start_consuming()

if __name__ == "__main__":
    main()
