#!/usr/bin/env bash
set -euo pipefail

# --- config ---
DEFAULT_VOICES=("en_US-lessac-medium" "de_DE-thorsten-high" "en_GB-cori-high")
VOICES_DIR="voices"
REQ_FILE="requirements.txt"

echo "==> Checking for uv..."
if ! command -v uv >/dev/null 2>&1; then
  echo "uv not found — installing..."
  curl -LsSf https://astral.sh/uv/install.sh | sh
  # shellcheck disable=SC1091
  [ -f "$HOME/.local/share/uv/env" ] && source "$HOME/.local/share/uv/env" || true
  command -v uv >/dev/null 2>&1 || { echo "uv install failed"; exit 1; }
fi
echo "uv: $(uv --version)"

echo "==> Installing Python deps..."
if [[ -f "$REQ_FILE" ]]; then
  uv pip install -r "$REQ_FILE"
else
  echo "No $REQ_FILE found; installing minimal deps (flask, numpy, piper)..."
  uv pip install flask numpy piper
fi

echo "==> Ensuring ALSA tools..."
if ! command -v aplay >/dev/null 2>&1; then
  sudo apt-get update
  sudo apt-get install -y alsa-utils
fi

echo "==> Creating voices dir..."
mkdir -p "$VOICES_DIR"

# Use CLI args as voices, else defaults
if [[ "$#" -gt 0 ]]; then
  VOICES=("$@")
else
  VOICES=("${DEFAULT_VOICES[@]}")
fi

echo "==> Downloading voices: ${VOICES[*]}"
for v in "${VOICES[@]}"; do
  uv run -m piper.download_voices --output "$VOICES_DIR" "$v"
done

echo "==> Done."
echo
echo "Run the server:"
echo "  uv run python server.py"
echo
echo "Test (mono):"
echo "  curl -X POST http://raspberrypi.local:5000/speak -H 'content-type: application/json' -d '{\"text\":\"hello\"}'"
echo
echo "Test (stereo):"
echo "  curl -X POST http://raspberrypi.local:5000/speak -H 'content-type: application/json' -d '{\"text\":[\"left\",\"right\"]}'"
