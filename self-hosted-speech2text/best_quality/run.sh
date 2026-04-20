#!/bin/bash
# Run best-quality STT (large-v3)
# Ensures conda's old libstdc++ doesn't break portaudio/jack
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
export LD_PRELOAD=/lib/x86_64-linux-gnu/libstdc++.so.6
exec "$HOME/.venvs/stt-best/bin/python3" "$SCRIPT_DIR/transcribe.py" "$@"
