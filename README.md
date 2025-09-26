# Piper HTTP Server

A lightweight Flask server that wraps [Piper](https://github.com/rhasspy/piper) text-to-speech and plays audio directly through ALSA (e.g. a Speaker Bonnet or Voice HAT) on a Raspberry Pi.  
Supports mono or stereo playback, different text per channel, and switching between installed voices.

---

## 🧰 Prerequisites

- Raspberry Pi Zero 2 W (or newer) running 64-bit Raspberry Pi OS  
- ALSA-compatible audio output (e.g. `plughw:1,0` for a Voice HAT)  
- Python ≥ 3.11  
- [`uv`](https://github.com/astral-sh/uv) package manager  
- `aplay` (from `alsa-utils`)

Install system deps:

```bash
sudo apt update
sudo apt install -y libportaudio2 alsa-utils
```

---

## 📦 Installation

Clone your project and install Python dependencies with `uv`:

```bash
git clone https://github.com/yourusername/piper-http-server.git
cd piper-http-server

# install dependencies
uv pip install -r requirements.txt
```

Download a voice into the `voices/` directory:

```bash
mkdir -p voices
uv run -m piper.download_voices --voice en_US-lessac-medium --output voices
```

(You can list available voices with `uv run -m piper.download_voices --list`.)

---

## ▶️ Running the server

Run directly with `uv` (no manual `venv` activation needed):

```bash
uv run python server.py
```

The server will start on port `5000`:

```
 * Running on http://0.0.0.0:5000
```

---

## 🌐 HTTP API

### `GET /voices`

List all available and loaded voices.

```bash
curl http://raspberrypi.local:5000/voices | jq
```

Response:
```json
{
  "default": "en_US_lessac_medium",
  "loaded": {},
  "available": {
    "en_US_lessac_medium": "voices/en_US-lessac-medium.onnx"
  }
}
```

---

### `POST /voices/load`

Preload a voice into memory.

```bash
curl -X POST http://raspberrypi.local:5000/voices/load \
  -H 'Content-Type: application/json' \
  -d '{"id": "en_US_lessac_medium"}'
```

---

### `DELETE /voices/<id>`

Unload a voice.

```bash
curl -X DELETE http://raspberrypi.local:5000/voices/en_US_lessac_medium
```

---

### `POST /speak`

Speak text on the device.  
- `"text"` can be a string → **mono** (plays on both speakers).  
- `"text"` can be an array of 2 strings → **stereo** (different text per channel).  

Optional fields:
- `"voice"` – choose which voice to use (defaults to the first found)
- `"device"` – ALSA device name (default: `"plughw:1,0"`)

#### 🗣️ Mono example
```bash
curl -X POST http://raspberrypi.local:5000/speak \
  -H "Content-Type: application/json" \
  -d '{"text": "hello julian"}'
```

#### 🎧 Stereo example
Different text on left and right channels:

```bash
curl -X POST http://raspberrypi.local:5000/speak \
  -H "Content-Type: application/json" \
  -d '{
    "text": ["left channel text", "right channel text"]
  }'
```

---

## 📁 Voices

The server automatically scans the `voices/` directory at startup and loads all `.onnx` voice files:

```
voices/
├─ en_US-lessac-medium.onnx
├─ en_US-amy-medium.onnx
```

The **first** voice found becomes the default.

---

## 🧪 Tips

- Check ALSA devices:  
  ```bash
  aplay -l
  ```
- Test audio output:  
  ```bash
  aplay -D plughw:1,0 /usr/share/sounds/alsa/Front_Center.wav
  ```
- Regenerate `requirements.txt` if needed:  
  ```bash
  uv pip freeze > requirements.txt
  ```

---

## 🛠️ Future ideas

- Add `/stop` endpoint to interrupt current playback  
- Queue synthesis requests instead of serializing with a lock  
- Support different voices per channel  

