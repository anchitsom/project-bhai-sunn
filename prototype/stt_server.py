"""Persistent STT server hosting IndicConformer 600M.

Promoted to the canonical STT path on 2026-04-30 after the A/B test on
2026-04-29 (see research/ab-results-2026-04-29.md). IndicConformer wins
on Hindi aspiration, proper-noun recognition, and latency. mlx-whisper
is decommissioned from this server. The Whisper code path is preserved
in git history at commit 80145e3 if it ever needs to come back.

Endpoints:
  GET  /health      warmed status, model identifier
  POST /transcribe  IndicConformer 600M, decoder=rnnt|ctc (default rnnt)

Run:
    .venv/bin/uvicorn prototype.stt_server:app --host 127.0.0.1 --port 8765

The HuggingFace token is read from ~/.cache/huggingface/token (set via
huggingface-cli login). No env var required.
"""

from __future__ import annotations

import subprocess
import time
from contextlib import asynccontextmanager
from pathlib import Path

import numpy as np
import torch
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from transformers import AutoModel

CONFORMER_MODEL = "ai4bharat/indic-conformer-600m-multilingual"
DEFAULT_DECODER = "rnnt"
DEFAULT_LANGUAGE = "hi"
SAMPLE_RATE = 16_000

VAD_FRAME_MS = 20
VAD_THRESHOLD_DB = -40.0
VAD_PADDING_MS = 200

_state: dict = {"model": None, "warmed": False}


def decode_to_numpy(src: Path) -> np.ndarray:
    """Decode any audio file to 16 kHz mono float32 numpy via ffmpeg pipe."""
    proc = subprocess.run(
        [
            "ffmpeg", "-loglevel", "error",
            "-i", str(src),
            "-f", "f32le",
            "-ar", str(SAMPLE_RATE),
            "-ac", "1",
            "-",
        ],
        check=True,
        capture_output=True,
    )
    return np.frombuffer(proc.stdout, dtype=np.float32)


def trim_silence(audio: np.ndarray) -> np.ndarray:
    if audio.size == 0:
        return audio
    frame = int(SAMPLE_RATE * VAD_FRAME_MS / 1000)
    pad = int(SAMPLE_RATE * VAD_PADDING_MS / 1000)
    n_frames = audio.size // frame
    if n_frames == 0:
        return audio
    framed = audio[: n_frames * frame].reshape(n_frames, frame)
    rms = np.sqrt(np.mean(framed.astype(np.float64) ** 2, axis=1) + 1e-12)
    db = 20.0 * np.log10(rms + 1e-12)
    speech = db > VAD_THRESHOLD_DB
    if not speech.any():
        return audio
    first = int(np.argmax(speech))
    last = int(n_frames - np.argmax(speech[::-1]))
    start = max(0, first * frame - pad)
    end = min(audio.size, last * frame + pad)
    return audio[start:end]


@asynccontextmanager
async def lifespan(app: FastAPI):
    model = AutoModel.from_pretrained(CONFORMER_MODEL, trust_remote_code=True)
    model.eval()
    silence = torch.zeros(1, SAMPLE_RATE)
    with torch.no_grad():
        model(silence, DEFAULT_LANGUAGE, DEFAULT_DECODER)
    _state["model"] = model
    _state["warmed"] = True
    yield


app = FastAPI(lifespan=lifespan)


class TranscribeRequest(BaseModel):
    path: str
    decoder: str = DEFAULT_DECODER
    language: str = DEFAULT_LANGUAGE
    vad_trim: bool = True


@app.get("/health")
def health() -> dict:
    return {
        "warmed": _state["warmed"],
        "model": CONFORMER_MODEL,
        "default_decoder": DEFAULT_DECODER,
        "default_language": DEFAULT_LANGUAGE,
    }


@app.post("/transcribe")
def transcribe(req: TranscribeRequest) -> dict:
    src = Path(req.path).expanduser()
    if not src.exists():
        raise HTTPException(404, f"file not found: {src}")
    if req.decoder not in {"ctc", "rnnt"}:
        raise HTTPException(400, "decoder must be 'ctc' or 'rnnt'")
    if not _state["warmed"]:
        raise HTTPException(503, "model not yet warmed")

    timings: dict[str, float] = {}

    t0 = time.time()
    audio = decode_to_numpy(src)
    timings["decode"] = round(time.time() - t0, 3)
    audio_seconds = round(audio.size / SAMPLE_RATE, 2)

    if req.vad_trim:
        t0 = time.time()
        audio = trim_silence(audio)
        timings["vad_trim"] = round(time.time() - t0, 3)

    wav = torch.from_numpy(audio).unsqueeze(0)

    t0 = time.time()
    with torch.no_grad():
        text = _state["model"](wav, req.language, req.decoder)
    timings["stt"] = round(time.time() - t0, 3)

    return {
        "text": str(text).strip(),
        "decoder": req.decoder,
        "language": req.language,
        "model": CONFORMER_MODEL,
        "audio_seconds_original": audio_seconds,
        "audio_seconds_trimmed": round(audio.size / SAMPLE_RATE, 2),
        "timings": timings,
    }
