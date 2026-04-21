#!/usr/bin/env python3
"""
Live/fast speech-to-text using faster-whisper small.en on CPU.
Optimized for near-realtime on CPU -- trades some accuracy for speed.
Transcription runs in the background so you can keep recording.
Result goes to: terminal, clipboard (xclip), and dated file.
"""

import sys
import os
import time
import wave
import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from stt_common import (get_key_nonblocking, record_audio, copy_to_clipboard,
                         save_to_file, save_audio, prompt_filename, mic_check,
                         cprint, queue_print, drain_output, has_pending_output,
                         SAMPLE_RATE, CHANNELS,
                         C_GREEN, C_YELLOW, C_RED, C_CYAN, C_DIM, C_TGREEN)

MODEL_SIZE = "small.en"
COMPUTE_TYPE = "int8"

_pending = 0
_pending_lock = threading.Lock()


def _adjust_pending(delta):
    global _pending
    with _pending_lock:
        _pending += delta
        return _pending


def _get_pending():
    with _pending_lock:
        return _pending


def _show_ready():
    """Print the ready prompt, including pending count if any."""
    n = _get_pending()
    if n > 0:
        cprint(f"Ready. Press SPACE to record...  [{n} transcribing]", C_GREEN)
    else:
        cprint("Ready. Press SPACE to record...", C_GREEN)


def _transcribe_job(model, wav_path, duration, filepath):
    """Runs in a background thread: transcribe, save, queue output."""
    try:
        # Save audio alongside transcript immediately (before transcription)
        audio_path = save_audio(wav_path, filepath)

        t0 = time.time()
        segments, info = model.transcribe(wav_path, language='en',
                                           beam_size=1, best_of=1,
                                           vad_filter=True)
        text_parts = [seg.text.strip() for seg in segments]
        text = ' '.join(text_parts)
        elapsed = time.time() - t0

        os.unlink(wav_path)

        if not text.strip():
            queue_print(f"(no speech detected — audio saved to {audio_path})", C_DIM, indent=True)
            return

        ratio = elapsed / duration if duration > 0 else 0
        queue_print(f"=== TRANSCRIPTION ({elapsed:.1f}s, {duration:.1f}s audio, {ratio:.1f}x) ===", C_TGREEN, indent=True)
        queue_print(text, C_TGREEN, indent=True)
        queue_print("=" * 50, C_TGREEN, indent=True)

        copy_to_clipboard(text)
        queue_print("Copied to clipboard.", C_DIM, indent=True)

        save_to_file(text, filepath)
        queue_print(f"Saved to {filepath}", C_DIM, indent=True)
    finally:
        _adjust_pending(-1)


def main():
    cprint(f"Loading faster-whisper {MODEL_SIZE} ({COMPUTE_TYPE})...", C_DIM)
    t0 = time.time()
    from faster_whisper import WhisperModel
    model = WhisperModel(MODEL_SIZE, device='cpu', compute_type=COMPUTE_TYPE,
                         cpu_threads=os.cpu_count())
    cprint(f"Model loaded in {time.time()-t0:.1f}s", C_DIM, indent=True)
    print()

    cprint("=" * 55, C_CYAN)
    cprint("  LIVE MODE (small.en, near-realtime)", C_CYAN)
    cprint("  Press SPACE to start recording", C_CYAN)
    cprint("  Press SPACE/d/ESC to stop recording", C_CYAN)
    cprint("  Press Ctrl+C or 'q' (when idle) to quit", C_CYAN)
    cprint("=" * 55, C_CYAN)
    print()

    if not mic_check():
        cprint("Continue anyway? (y/n)", C_RED)
        while True:
            key = get_key_nonblocking(0.1)
            if key in ('y', 'Y', ' '):
                break
            if key in ('n', 'N', 'q', 'Q', '\x03', 'ESC'):
                cprint("Bye!", C_RED)
                return

    executor = ThreadPoolExecutor(max_workers=1)

    while True:
        # Drain any completed background output, then show ready prompt
        print()
        drain_output()
        _show_ready()

        # Idle loop: wait for SPACE, draining background output as it arrives
        while True:
            key = get_key_nonblocking(0.1)
            if key == ' ':
                break
            if key in ('q', 'Q') or key == '\x03':
                executor.shutdown(wait=True)
                drain_output()
                cprint("Bye!", C_RED)
                return
            # Drain background output while idle — reprint ready if something appeared
            if drain_output():
                _show_ready()

        audio = record_audio()
        if audio is None or len(audio) < SAMPLE_RATE * 0.3:
            cprint("Too short, skipped.", C_DIM, indent=True)
            continue

        duration = len(audio) / SAMPLE_RATE
        cprint(f"Recorded {duration:.1f}s of audio.", C_DIM, indent=True)

        # Write wav for transcription
        tmp = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
        with wave.open(tmp.name, 'w') as wf:
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(2)
            wf.setframerate(SAMPLE_RATE)
            audio_int16 = (audio * 32767).astype(np.int16)
            wf.writeframes(audio_int16.tobytes())

        # Ask for filename (transcription hasn't started yet but will run
        # concurrently once submitted — the prompt is quick)
        filepath = prompt_filename()

        # Submit to background
        _adjust_pending(1)
        cprint("Transcription queued in background...", C_DIM, indent=True)
        executor.submit(_transcribe_job, model, tmp.name, duration, filepath)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        cprint("\nBye!", C_RED)
