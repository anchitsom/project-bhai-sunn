"""Persistent STT server hosting two ASR providers for the A/B harness.

Endpoints:
  GET  /health                   warmed status, available providers
  POST /transcribe               Whisper large-v3-turbo via mlx-whisper
  POST /transcribe-conformer     IndicConformer 600M (CTC or RNNT) via HF transformers

Whisper-side optimisations vs the standalone test_pipeline.py:
  1. Single transcription per request (no A/B).
  2. Model loaded once at startup; stays resident across requests.
  3. No intermediate WAV file. Audio decoded from any source format
     directly into a numpy array via an ffmpeg pipe, then handed straight
     to mlx-whisper.
  4. Optional energy-based edge-silence trim (numpy only, no external VAD lib).

Conformer-side notes:
  * Lazy load on first request — model is gated on HuggingFace, so we do
    not block startup. If HF_TOKEN is missing or invalid the endpoint
    returns 503 with a gate-instruction message; once auth lands, the
    next request loads the model and subsequent requests run warm.
  * Both CTC and RNNT decoders are exposed; the request body's `decoder`
    field selects.

Run:
    .venv/bin/uvicorn prototype.stt_server:app --host 127.0.0.1 --port 8765
"""

from __future__ import annotations

import subprocess
import time
from contextlib import asynccontextmanager
from pathlib import Path

import mlx_whisper
import numpy as np
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

WHISPER_MODEL = "mlx-community/whisper-large-v3-turbo"
CONFORMER_MODEL = "ai4bharat/indic-conformer-600m-multilingual"
LANGUAGE = "hi"
SAMPLE_RATE = 16_000

VAD_FRAME_MS = 20
VAD_THRESHOLD_DB = -40.0
VAD_PADDING_MS = 200

_conformer_state: dict = {"model": None, "load_error": None}


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
    """Energy-threshold edge-silence trim. Removes leading/trailing silence
    only; does not touch internal pauses (Whisper handles those fine)."""
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


_warmed = False


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _warmed
    silence = np.zeros(SAMPLE_RATE, dtype=np.float32)
    mlx_whisper.transcribe(
        silence,
        path_or_hf_repo=WHISPER_MODEL,
        language=LANGUAGE,
    )
    _warmed = True
    yield


app = FastAPI(lifespan=lifespan)


class TranscribeRequest(BaseModel):
    path: str
    vad_trim: bool = True


def _load_conformer():
    """Lazy-load IndicConformer. Idempotent. Stores the model in module
    state so repeat calls return immediately. Errors are sticky — once a
    load fails (e.g. gate auth), we keep returning the same error rather
    than retrying every request."""
    if _conformer_state["model"] is not None:
        return _conformer_state["model"]
    if _conformer_state["load_error"] is not None:
        raise _conformer_state["load_error"]
    try:
        import torch
        from transformers import AutoModel
        model = AutoModel.from_pretrained(
            CONFORMER_MODEL,
            trust_remote_code=True,
        )
        model.eval()
        _conformer_state["model"] = model
        return model
    except Exception as exc:
        _conformer_state["load_error"] = exc
        raise


@app.get("/health")
def health() -> dict:
    return {
        "warmed": _warmed,
        "providers": {
            "whisper": {"model": WHISPER_MODEL, "language": LANGUAGE, "ready": _warmed},
            "conformer": {
                "model": CONFORMER_MODEL,
                "loaded": _conformer_state["model"] is not None,
                "load_error": str(_conformer_state["load_error"])
                if _conformer_state["load_error"] is not None
                else None,
            },
        },
    }


@app.post("/transcribe")
def transcribe(req: TranscribeRequest) -> dict:
    src = Path(req.path).expanduser()
    if not src.exists():
        raise HTTPException(404, f"file not found: {src}")

    timings: dict[str, float] = {}

    t0 = time.time()
    audio = decode_to_numpy(src)
    timings["decode"] = round(time.time() - t0, 3)
    audio_seconds = round(audio.size / SAMPLE_RATE, 2)

    if req.vad_trim:
        t0 = time.time()
        audio = trim_silence(audio)
        timings["vad_trim"] = round(time.time() - t0, 3)

    t0 = time.time()
    result = mlx_whisper.transcribe(
        audio,
        path_or_hf_repo=WHISPER_MODEL,
        language=LANGUAGE,
    )
    timings["stt"] = round(time.time() - t0, 3)

    return {
        "text": result["text"].strip(),
        "audio_seconds_original": audio_seconds,
        "audio_seconds_trimmed": round(audio.size / SAMPLE_RATE, 2),
        "timings": timings,
    }


class ConformerRequest(BaseModel):
    path: str
    decoder: str = "rnnt"
    language: str = "hi"


@app.post("/transcribe-conformer")
def transcribe_conformer(req: ConformerRequest) -> dict:
    src = Path(req.path).expanduser()
    if not src.exists():
        raise HTTPException(404, f"file not found: {src}")
    if req.decoder not in {"ctc", "rnnt"}:
        raise HTTPException(400, "decoder must be 'ctc' or 'rnnt'")

    try:
        model = _load_conformer()
    except Exception as exc:
        msg = str(exc)
        if "gated" in msg.lower() or "401" in msg or "Cannot access" in msg:
            raise HTTPException(
                503,
                "IndicConformer model is gated on HuggingFace. "
                "Accept the gate at https://huggingface.co/ai4bharat/indic-conformer-600m-multilingual "
                "and set HF_TOKEN before launching the server.",
            )
        raise HTTPException(503, f"conformer model load failed: {msg}")

    timings: dict[str, float] = {}

    t0 = time.time()
    audio = decode_to_numpy(src)
    timings["decode"] = round(time.time() - t0, 3)
    audio_seconds = round(audio.size / SAMPLE_RATE, 2)

    import torch

    wav = torch.from_numpy(audio).unsqueeze(0)

    t0 = time.time()
    with torch.no_grad():
        text = model(wav, req.language, req.decoder)
    timings["stt"] = round(time.time() - t0, 3)

    return {
        "text": str(text).strip(),
        "decoder": req.decoder,
        "language": req.language,
        "audio_seconds": audio_seconds,
        "timings": timings,
    }
