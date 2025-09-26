# server.py
import subprocess
import os
from flask import Flask, request, jsonify
from piper.voice import PiperVoice

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL = os.path.join(BASE_DIR, "en_US-lessac-medium.onnx")
ALSA  = "plughw:1,0"

voice = PiperVoice.load(MODEL)
sr = getattr(voice.config, "sample_rate",
     getattr(voice.config, "sample_rate_hz", 22050))

app = Flask(__name__)

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
