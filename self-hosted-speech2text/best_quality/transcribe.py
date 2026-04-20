#!/usr/bin/env python3
"""
Best-quality speech-to-text using faster-whisper large-v3 on CPU.
Press SPACE to start recording, press SPACE/ESC/d to stop.
Result goes to: terminal, clipboard (xclip), and dated file.
"""

import sys
import os
import time
import wave
import tempfile

import numpy as np

# Add parent dir so we can import shared code
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from stt_common import (get_key_nonblocking, record_audio, copy_to_clipboard,
                         save_to_file, SAMPLE_RATE, CHANNELS)

MODEL_SIZE = "large-v3"
COMPUTE_TYPE = "int8"


def main():
    print(f"Loading faster-whisper {MODEL_SIZE} ({COMPUTE_TYPE})...")
    t0 = time.time()
    from faster_whisper import WhisperModel
    model = WhisperModel(MODEL_SIZE, device='cpu', compute_type=COMPUTE_TYPE,
                         cpu_threads=os.cpu_count())
    print(f"  Model loaded in {time.time()-t0:.1f}s\n")

    print("=" * 55)
    print("  BEST QUALITY MODE (large-v3, slower than realtime)")
    print("  Press SPACE to start recording")
    print("  Press SPACE/d/ESC to stop recording")
    print("  Press Ctrl+C or 'q' (when idle) to quit")
    print("=" * 55)

    while True:
        print("\nReady. Press SPACE to record...")
        while True:
            key = get_key_nonblocking(0.1)
            if key == ' ':
                break
            if key in ('q', 'Q') or key == '\x03':
                print("\nBye!")
                return

        audio = record_audio()
        if audio is None or len(audio) < SAMPLE_RATE * 0.3:
            print("  Too short, skipped.")
            continue

        duration = len(audio) / SAMPLE_RATE
        print(f"  Recorded {duration:.1f}s of audio.")

        tmp = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
        with wave.open(tmp.name, 'w') as wf:
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(2)
            wf.setframerate(SAMPLE_RATE)
            audio_int16 = (audio * 32767).astype(np.int16)
            wf.writeframes(audio_int16.tobytes())

        print(f"  Transcribing with {MODEL_SIZE} (this may take a while)...")
        t0 = time.time()
        segments, info = model.transcribe(tmp.name, language='en',
                                           beam_size=5, best_of=5,
                                           vad_filter=True)
        text_parts = [seg.text.strip() for seg in segments]
        text = ' '.join(text_parts)
        elapsed = time.time() - t0

        os.unlink(tmp.name)

        if not text.strip():
            print("  (no speech detected)")
            continue

        print(f"\n  === TRANSCRIPTION ({elapsed:.1f}s, {duration:.1f}s audio) ===")
        print(f"  {text}")
        print(f"  {'=' * 50}")

        copy_to_clipboard(text)
        print("  Copied to clipboard.")

        fpath = save_to_file(text)
        print(f"  Saved to {fpath}")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\nBye!")
