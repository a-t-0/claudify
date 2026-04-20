#!/bin/bash
# Run live/fast STT (small.en)
# Ensures conda's old libstdc++ doesn't break portaudio/jack
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
export LD_PRELOAD=/lib/x86_64-linux-gnu/libstdc++.so.6
exec "$HOME/.venvs/stt-live/bin/python3" "$SCRIPT_DIR/transcribe.py" "$@"
