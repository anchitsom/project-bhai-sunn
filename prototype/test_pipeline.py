"""Phase 0 smoke test for Bhai Sunn.

Runs on Mac Studio alone. Records 5 seconds from the default mic, transcribes
with mlx-whisper (Hindi), sends the text to Ollama (Gemma 2 9B) with a
Hindi-leaning system prompt, then speaks the reply through Piper.

Pre-reqs (see bootstrap.md, Phase 0):
  - mlx-whisper installed:           pip install mlx-whisper
  - piper-tts installed:             pip install piper-tts (or brew install piper-tts)
  - hi_IN-pratham-medium voice at:   ~/.local/share/piper-voices/hi_IN-pratham-medium.onnx
  - ollama running on localhost:11434 with gemma2:9b pulled
  - sounddevice installed:           pip install sounddevice numpy soundfile

Usage:
  python prototype/test_pipeline.py
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

import numpy as np
import sounddevice as sd
import soundfile as sf

SAMPLE_RATE = 16_000
RECORD_SECONDS = 5
WHISPER_MODEL = "mlx-community/whisper-large-v3-turbo"
OLLAMA_URL = "http://localhost:11434/api/chat"
OLLAMA_MODEL = "gemma2:9b"
PIPER_VOICE = Path.home() / ".local/share/piper-voices/hi_IN-pratham-medium.onnx"

SYSTEM_PROMPT = (
    "Tum 'Bhai Sunn' ho — ek Hindi-bolne wala ghar ka sahayak. "
    "User Hindi ya Hinglish mein baat karega. Tum hamesha Hindi mein, "
    "chhote aur seedhe jawab dena. Ek-do vakya kaafi hain. "
    "Agar koi tareekh, samay, ya basic factoid maange aur tumhe sahi pata "
    "nahi hai, to imaandari se bolo ki abhi tumhare paas wo jaankari nahi hai."
)


def record_audio() -> Path:
    print(f"\n[record] {RECORD_SECONDS} seconds. Hindi mein boliye...")
    audio = sd.rec(
        int(RECORD_SECONDS * SAMPLE_RATE),
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype="float32",
    )
    sd.wait()
    tmp = Path(tempfile.mkstemp(suffix=".wav")[1])
    sf.write(tmp, audio, SAMPLE_RATE)
    print(f"[record] saved {tmp}")
    return tmp


def transcribe(wav_path: Path) -> str:
    import mlx_whisper

    t0 = time.time()
    result = mlx_whisper.transcribe(
        str(wav_path),
        path_or_hf_repo=WHISPER_MODEL,
        language="hi",
    )
    text = result["text"].strip()
    print(f"[stt] {time.time() - t0:.2f}s -> {text!r}")
    return text


def ask_llm(user_text: str) -> str:
    payload = {
        "model": OLLAMA_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_text},
        ],
        "stream": False,
    }
    req = urllib.request.Request(
        OLLAMA_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=60) as resp:
        body = json.loads(resp.read())
    reply = body["message"]["content"].strip()
    print(f"[llm] {time.time() - t0:.2f}s -> {reply!r}")
    return reply


def speak(text: str) -> None:
    if not PIPER_VOICE.exists():
        print(f"[tts] piper voice not found at {PIPER_VOICE}")
        sys.exit(1)
    out_wav = Path(tempfile.mkstemp(suffix=".wav")[1])
    t0 = time.time()
    proc = subprocess.run(
        [
            "piper",
            "--model", str(PIPER_VOICE),
            "--output_file", str(out_wav),
        ],
        input=text.encode("utf-8"),
        check=True,
    )
    print(f"[tts] {time.time() - t0:.2f}s -> {out_wav}")
    audio, sr = sf.read(out_wav)
    sd.play(audio, sr)
    sd.wait()


def main() -> None:
    if not PIPER_VOICE.exists():
        sys.exit(
            f"piper voice missing at {PIPER_VOICE}; "
            "see bootstrap.md Phase 0 step 1"
        )

    wav = record_audio()
    transcript = transcribe(wav)
    if not transcript:
        sys.exit("empty transcript; nothing to send to LLM")
    reply = ask_llm(transcript)
    speak(reply)
    print("\n[done] Phase 0 smoke test complete.")


if __name__ == "__main__":
    main()
