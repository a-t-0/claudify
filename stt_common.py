"""
Shared utilities for both STT variants: file saving, clipboard, key input.
"""

import sys
import os
import subprocess
import termios
import tty
import select
import threading
import readline
from datetime import datetime

import numpy as np
import sounddevice as sd

OUTPUT_DIR = os.path.expanduser("~/stt_transcripts")
SAMPLE_RATE = 16000
CHANNELS = 1


def get_key_nonblocking(timeout=0.05):
    """Read a single keypress without blocking."""
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        if select.select([sys.stdin], [], [], timeout)[0]:
            ch = sys.stdin.read(1)
            if ch == '\x1b':
                if select.select([sys.stdin], [], [], 0.02)[0]:
                    sys.stdin.read(1)
                    if select.select([sys.stdin], [], [], 0.02)[0]:
                        sys.stdin.read(1)
                return 'ESC'
            return ch
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)
    return None


def record_audio():
    """Record audio until stop key pressed. Returns numpy array."""
    chunks = []
    stop_flag = threading.Event()

    def callback(indata, frames, time_info, status):
        if not stop_flag.is_set():
            chunks.append(indata.copy())

    print("  Recording... (press SPACE, 'd', or ESC to stop)")
    stream = sd.InputStream(samplerate=SAMPLE_RATE, channels=CHANNELS,
                            dtype='float32', callback=callback)
    stream.start()

    while not stop_flag.is_set():
        key = get_key_nonblocking(0.05)
        if key in (' ', 'd', 'D', 'ESC', 'q', 'Q'):
            stop_flag.set()

    stream.stop()
    stream.close()

    if not chunks:
        return None
    return np.concatenate(chunks, axis=0).flatten()


def copy_to_clipboard(text):
    """Copy text to X11 clipboard."""
    try:
        p = subprocess.Popen(['xclip', '-selection', 'clipboard'],
                             stdin=subprocess.PIPE)
        p.communicate(text.encode('utf-8'))
    except FileNotFoundError:
        print("  (xclip not found, skipping clipboard)")


def prompt_filename():
    """
    Ask user for optional categorisation after transcription.

    Supports:
      - ENTER alone  -> just date: 2026-04-20_13-45-02.txt
      - "login bug"  -> 2026-04-20_13-45-02_login-bug.txt
      - "US-123/login bug" -> US-123/2026-04-20_13-45-02_login-bug.txt
      - "sprint-4/US-123/regression" -> sprint-4/US-123/2026-04-20_13-45-02_regression.txt

    The last segment is the subject, everything before it becomes nested dirs.
    """
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    print()
    print("  Filename: press ENTER for default, or type category/subject")
    print("  Examples:  login bug")
    print("             US-123/login bug")
    print("             sprint-4/US-123/checkout regression")

    try:
        raw = input("  > ").strip()
    except (EOFError, KeyboardInterrupt):
        raw = ""

    if not raw:
        return os.path.join(OUTPUT_DIR, f"{ts}.txt")

    # Split on / to get nested path segments
    parts = [p.strip() for p in raw.split('/') if p.strip()]

    # Last part is the subject, rest are directory segments
    subject = parts[-1] if parts else ""
    dirs = parts[:-1] if len(parts) > 1 else []

    # Sanitize subject: lowercase, spaces to hyphens, keep alphanumeric/-/_
    safe_subject = subject.lower().replace(' ', '-')
    safe_subject = ''.join(c for c in safe_subject if c.isalnum() or c in '-_')

    # Sanitize dir segments the same way
    safe_dirs = []
    for d in dirs:
        safe_d = d.strip().replace(' ', '-')
        safe_d = ''.join(c for c in safe_d if c.isalnum() or c in '-_')
        if safe_d:
            safe_dirs.append(safe_d)

    if safe_subject:
        filename = f"{ts}_{safe_subject}.txt"
    else:
        filename = f"{ts}.txt"

    filepath = os.path.join(OUTPUT_DIR, *safe_dirs, filename)
    return filepath


def save_to_file(text):
    """Save transcript with user-chosen categorised filename."""
    filepath = prompt_filename()
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w') as f:
        f.write(text + '\n')
    return filepath
