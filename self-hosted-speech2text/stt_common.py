"""
Shared utilities for both STT variants: file saving, clipboard, key input, colors.
"""

import sys
import os
import subprocess
import termios
import tty
import select
import threading
import queue
import readline
from datetime import datetime

import numpy as np
import sounddevice as sd

OUTPUT_DIR = os.path.expanduser("~/stt_transcripts")
SAMPLE_RATE = 16000
CHANNELS = 1

# ── ANSI colors ──────────────────────────────────────────────────────
C_RESET   = "\033[0m"
C_GREEN   = "\033[1;32m"   # status: ready / go
C_YELLOW  = "\033[1;33m"   # status: recording / active
C_RED     = "\033[1;31m"   # status: quit / stop
C_CYAN    = "\033[1;36m"   # header banner
C_DIM     = "\033[2m"      # processing info (indented)
C_TGREEN  = "\033[0;32m"   # transcription text (indented, non-bold)

# ── Output queue ─────────────────────────────────────────────────────
# Background threads must NEVER print directly. They put messages here,
# and the foreground drains the queue when it's safe (idle loop).
_output_queue = queue.Queue()


def queue_print(msg, color="", indent=False):
    """Queue a message for the foreground to print later."""
    _output_queue.put((msg, color, indent))


def drain_output():
    """Print all queued messages. Call ONLY from the foreground thread."""
    printed = False
    while True:
        try:
            msg, color, indent = _output_queue.get_nowait()
        except queue.Empty:
            break
        prefix = "    " if indent else ""
        if color:
            print(f"{color}{prefix}{msg}{C_RESET}", flush=True)
        else:
            print(f"{prefix}{msg}", flush=True)
        printed = True
    return printed


def has_pending_output():
    """Check if there are queued messages without consuming them."""
    return not _output_queue.empty()


def cprint(msg, color="", indent=False):
    """Immediate colored print. Only use from the foreground thread."""
    prefix = "    " if indent else ""
    if color:
        print(f"{color}{prefix}{msg}{C_RESET}", flush=True)
    else:
        print(f"{prefix}{msg}", flush=True)


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

    cprint("Recording... (press SPACE, 'd', or ESC to stop)", C_YELLOW)
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
        pass  # silently skip if xclip missing


def build_filepath(raw_input):
    """
    Turn user input into a filepath for the transcript.

    Supports:
      - "" (empty)         -> just date: 2026-04-20_13-45-02.txt
      - "login bug"        -> 2026-04-20_13-45-02_login-bug.txt
      - "US-123/login bug" -> US-123/2026-04-20_13-45-02_login-bug.txt
    """
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    if not raw_input:
        return os.path.join(OUTPUT_DIR, f"{ts}.txt")

    parts = [p.strip() for p in raw_input.split('/') if p.strip()]
    subject = parts[-1] if parts else ""
    dirs = parts[:-1] if len(parts) > 1 else []

    safe_subject = subject.lower().replace(' ', '-')
    safe_subject = ''.join(c for c in safe_subject if c.isalnum() or c in '-_')

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

    return os.path.join(OUTPUT_DIR, *safe_dirs, filename)


def prompt_filename():
    """
    Ask user for optional categorisation after transcription.
    Returns the filepath string.
    """
    print()
    cprint("Filename: press ENTER for default, or type category/subject", C_YELLOW)
    cprint("Examples:  login bug", C_DIM, indent=True)
    cprint("           US-123/login bug", C_DIM, indent=True)
    cprint("           sprint-4/US-123/checkout regression", C_DIM, indent=True)

    try:
        raw = input(f"  {C_YELLOW}>{C_RESET} ").strip()
    except (EOFError, KeyboardInterrupt):
        raw = ""

    return build_filepath(raw)


def save_to_file(text, filepath):
    """Save transcript to the given filepath."""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w') as f:
        f.write(text + '\n')
    return filepath
