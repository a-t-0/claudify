#!/bin/bash
set -e

echo "=== Best Quality STT Install (faster-whisper large-v3, CPU) ==="

# System deps
echo -e "\n[1/4] System dependencies..."
sudo apt update && sudo apt install -y ffmpeg libsndfile1 xclip portaudio19-dev

# Python venv
VENV_DIR="$HOME/.venvs/stt-best"
echo -e "\n[2/4] Creating Python venv at $VENV_DIR..."
python3 -m venv "$VENV_DIR"
source "$VENV_DIR/bin/activate"

# Install packages
echo -e "\n[3/4] Installing Python packages..."
pip install --upgrade pip
pip install faster-whisper sounddevice numpy

# Pre-download the large-v3 model
echo -e "\n[4/4] Pre-downloading large-v3 model (this downloads ~3GB on first run)..."
python3 -c "
from faster_whisper import WhisperModel
print('Downloading large-v3 model...')
model = WhisperModel('large-v3', device='cpu', compute_type='int8')
print('Model loaded and cached successfully!')
import numpy as np
audio = np.zeros(16000, dtype=np.float32)
segments, info = model.transcribe(audio, language='en')
list(segments)
print('Inference test passed!')
"

echo -e "\n=== Installation complete! ==="
echo ""
echo "Usage:  cd $(cd "$(dirname "$0")" && pwd) && ./run.sh"
