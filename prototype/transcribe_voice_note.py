"""Transcribe a Telegram voice note with mlx-whisper, with optional denoising A/B.

Usage:
    transcribe_voice_note.py <audio_file>

Pipeline:
    1. ffmpeg: source audio -> 16 kHz mono WAV
    2. (a) raw WAV -> mlx-whisper large-v3-turbo, language='hi'
       (b) noisereduce-denoised WAV -> mlx-whisper, language='hi'
    3. Print both transcripts and per-stage latencies as JSON

Notes:
    - mlx-whisper auto-downloads `mlx-community/whisper-large-v3-turbo` on
      first run (~1.6 GB).
    - `noisereduce` is spectral gating, not SOTA. We swap for DeepFilterNet 3
      once a 3.13-compatible wheel exists (or once we add python@3.11).
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import mlx_whisper
import noisereduce as nr
import numpy as np
import soundfile as sf

WHISPER_MODEL = "mlx-community/whisper-large-v3-turbo"
LANGUAGE = "hi"
TARGET_SR = 16_000


def to_wav(src: Path) -> Path:
    out = Path(tempfile.mkstemp(suffix=".wav")[1])
    subprocess.run(
        [
            "ffmpeg", "-y", "-loglevel", "error",
            "-i", str(src),
            "-ar", str(TARGET_SR),
            "-ac", "1",
            "-f", "wav",
            str(out),
        ],
        check=True,
    )
    return out


def denoise(wav_path: Path) -> Path:
    audio, sr = sf.read(wav_path)
    cleaned = nr.reduce_noise(
        y=audio,
        sr=sr,
        stationary=False,
        prop_decrease=0.85,
    )
    out = Path(tempfile.mkstemp(suffix=".wav")[1])
    sf.write(out, cleaned, sr)
    return out


def transcribe(wav_path: Path) -> tuple[str, float]:
    t0 = time.time()
    result = mlx_whisper.transcribe(
        str(wav_path),
        path_or_hf_repo=WHISPER_MODEL,
        language=LANGUAGE,
    )
    return result["text"].strip(), time.time() - t0


def main() -> None:
    if len(sys.argv) != 2:
        print("usage: transcribe_voice_note.py <audio_file>", file=sys.stderr)
        sys.exit(2)

    src = Path(sys.argv[1]).expanduser()
    if not src.exists():
        print(f"file not found: {src}", file=sys.stderr)
        sys.exit(1)

    timings: dict[str, float] = {}

    t0 = time.time()
    raw_wav = to_wav(src)
    timings["ffmpeg_to_wav"] = time.time() - t0

    t0 = time.time()
    den_wav = denoise(raw_wav)
    timings["denoise"] = time.time() - t0

    raw_text, raw_t = transcribe(raw_wav)
    timings["stt_raw"] = raw_t

    den_text, den_t = transcribe(den_wav)
    timings["stt_denoised"] = den_t

    out = {
        "model": WHISPER_MODEL,
        "language": LANGUAGE,
        "denoiser": "noisereduce (spectral gating)",
        "source": str(src),
        "transcripts": {
            "raw": raw_text,
            "denoised": den_text,
        },
        "timings_seconds": {k: round(v, 2) for k, v in timings.items()},
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
