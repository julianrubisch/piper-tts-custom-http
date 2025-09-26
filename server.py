# server.py
import subprocess
import os
from pathlib import Path
from flask import Flask, request, jsonify
from piper.voice import PiperVoice

BASE_DIR = Path(__file__).resolve().parent
VOICES_DIR = BASE_DIR / "voices"

AVAILABLE_VOICES = {
    path.stem.replace("-", "_"): path
    for path in VOICES_DIR.glob("*.onnx")
}

DEFAULT_VOICE = next(iter(AVAILABLE_VOICES)) if AVAILABLE_VOICES else None

VOICES = {}            # id -> PiperVoice
VOICE_META = {}        # id -> {"rate": int, "channels": int, "sample_width": int}
# play_lock = threading.Lock()

def get_voice(vid: str) -> tuple[PiperVoice, dict]:
    if vid not in VOICES:
        path = AVAILABLE_VOICES.get(vid)
        if not path or not Path(path).exists():
            raise FileNotFoundError(f"voice {vid} not found")
        v = PiperVoice.load(str(path))
        # peek one frame to learn format without consuming text later
        # (we’ll read format at runtime from first chunk anyway)
        VOICES[vid] = v
        # lazy meta; filled on first synth
        VOICE_META.setdefault(vid, {})
    return VOICES[vid], VOICE_META[vid]

# MODEL = os.path.join(BASE_DIR, "en_US-lessac-medium.onnx")

ALSA  = "plughw:1,0"

print("Loading default voice")
voice = get_voice(DEFAULT_VOICE)[0]
print("Finished loading default voice")
app = Flask(__name__)

@app.get("/voices")
def voices():
    return jsonify({
        "default": DEFAULT_VOICE,
        "loaded": VOICE_META,
        "available": {k: str(v) for k, v in AVAILABLE_VOICES.items()}
    })

@app.post("/speak")
def speak():
    text = ""

    # Prefer JSON
    if request.is_json:
        data = request.get_json(silent=True) or {}
        text = (data.get("text") or "").strip()
    else:
        # Fallbacks: form or raw body as plain text
        text = (request.form.get("text")
                or request.args.get("text")
                or request.get_data(as_text=True)).strip()

    if not text:
        return jsonify({"error": "empty text"}), 400

    # Stream chunks
    gen = voice.synthesize(text)
    try:
        first = next(gen)
    except StopIteration:
        return jsonify({"error": "no audio produced"}), 500

    # Map sample width to aplay fmt (Piper is int16, but be defensive)
    sw = first.sample_width
    if sw == 2:
        fmt = "S16_LE"
    elif sw == 1:
        fmt = "U8"
    elif sw == 4:
        fmt = "S32_LE"
    else:
        return jsonify({"error": f"unsupported sample_width={sw}"}), 500

    rate = first.sample_rate
    ch   = first.sample_channels

    # Start aplay for raw PCM
    aplay = subprocess.Popen(
        ["aplay", "-q", "-D", ALSA, "-r", str(rate), "-f", fmt, "-c", str(ch), "-t", "raw", "-"],
        stdin=subprocess.PIPE,
    )

    # write first + remaining chunks
    aplay.stdin.write(first.audio_int16_bytes)
    for chunk in gen:
        aplay.stdin.write(chunk.audio_int16_bytes)

    aplay.stdin.close()
    aplay.wait()
    return jsonify({"ok": True, "rate": rate, "channels": ch, "format": fmt})

if __name__ == "__main__":
    # bind on all interfaces; disable reloader so the model loads once
    app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)
