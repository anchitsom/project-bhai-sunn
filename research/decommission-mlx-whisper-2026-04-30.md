# Decommission Log: mlx-whisper to IndicConformer 600M

**Date:** 2026-04-30
**Owners:** Anchit Som, Adamya Tripathi
**Decision:** Promote AI4Bharat IndicConformer 600M (RNNT decoder) to the default STT model for project-bhai-sunn. Decommission mlx-whisper from the production wire. Run the STT service under launchd as `com.anchit.bhai-sunn-stt` so it stays up across reboots and is the canonical transcription path for Telegram voice notes and Promptfoo evals.

---

## Why

The A/B run on 2026-04-29 (`research/ab-results-2026-04-29.md`) compared Whisper large-v3-turbo (mlx-whisper, 809M params, MIT) against IndicConformer 600M (RNNT and CTC, 600M params, MIT) on two Hindi voice notes from the same recording surface (Telegram on iPhone, Opus codec, 2-3 second utterances). Conformer won on three measurable axes:

1. **Aspirated consonants preserved.** "भाई" (bhai) rendered correctly. Whisper consistently dropped the aspiration to "बाई" (bai = lady).
2. **Indic proper-noun recognition.** "Adamya" rendered as "अदम्या". Whisper hallucinated to "अदम्यागी", a non-word that is phonetically nearby and semantically meaningless.
3. **Latency.** Conformer RNNT 184ms STT, Conformer CTC 128-150ms STT, Whisper-MLX 465-523ms STT. **3x faster on the same Mac Studio M1 Max.**

The latency result was counter-intuitive — MLX on Apple Silicon was expected to win against PyTorch CPU. The explanation is in `research/primer-gguf-pytorch-ollama-mlx.md`: Whisper's autoregressive transformer decoder pays per-output-token attention overhead that dominates on short utterances, while Conformer's RNNT/CTC decoders are non-autoregressive or near-non-autoregressive. Algorithmic shape beat hardware acceleration.

---

## What changed

### Server

Before:
- `prototype/stt_server.py` exposed both `/transcribe` (mlx-whisper) and `/transcribe-conformer` (IndicConformer)
- mlx-whisper was the default; Conformer was a candidate behind a separate path

After:
- `/transcribe` is the only canonical endpoint, served by IndicConformer 600M (RNNT default, CTC opt-in via `decoder` param)
- mlx-whisper code removed from the server entirely (the file at HEAD no longer imports `mlx_whisper`)
- Whisper-on-server preserved at git commit `80145e3` for historical reference; can be restored with a checkout

### Always-on service

Before:
- Server ran as a foreground uvicorn invocation in a Bash background task; stopped between sessions

After:
- launchd plist at `~/Library/LaunchAgents/com.anchit.bhai-sunn-stt.plist`
- Wrapper script at `~/services/bhai-sunn-stt/start.sh`
- Logs at `~/services/bhai-sunn-stt/{stdout,stderr}.log`
- `KeepAlive=true`, `RunAtLoad=true` — survives reboots
- Bound to `127.0.0.1:8765` (no auth on the wire, so localhost-only per the project's bind-host rule)
- Registered in `system/services-and-ports.md`

### HuggingFace offline mode

Before:
- Server depended on a live HF token to authenticate against the gated `ai4bharat/indic-conformer-600m-multilingual` repo on every load

After:
- Model fully cached in `~/.cache/huggingface/hub/`
- Plist sets `HF_HUB_OFFLINE=1` and `TRANSFORMERS_OFFLINE=1`
- The HF token can now be rotated freely; the server reads from cache and never calls HF

### Documentation

Updated:
- `CLAUDE.md` — joint-project credit for Anchit and Adamya, status tracker through 2026-04-30, core stack reflects Conformer
- `README.md` — STT row updated, A/B reference added
- `architecture.md` — diagrams, RAM budget (now ~8.1 GB resident), trade-off table replaced with the Conformer/Whisper/Seamless comparison
- `bootstrap.md` — Phase 0 install steps now use transformers + torch + onnxruntime path; HF gate-acceptance step added
- `system/services-and-ports.md` — new launchd row for `com.anchit.bhai-sunn-stt`

Created:
- `research/decommission-mlx-whisper-2026-04-30.md` (this file)
- `research/primer-gguf-pytorch-ollama-mlx.md` — explainer for why this works the way it works

### Behavioural rule

Telegram voice notes received from the user are now automatically downloaded, transcribed via the Conformer endpoint, and replied with the transcript — no user prompt required for each voice note. Saved as a feedback memory.

---

## Reversion path

If we ever need Whisper back:

1. `git checkout 80145e3 -- prototype/stt_server.py` (or `git revert` the relevant commits)
2. `pip install mlx-whisper` in the venv
3. Either replace the canonical endpoint or expose Whisper alongside Conformer
4. Restart the launchd service: `launchctl kickstart -k gui/$(id -u)/com.anchit.bhai-sunn-stt`

The mlx-whisper Python package is uninstalled but the test scripts (`test_pipeline.py`, `transcribe_voice_note.py`) still reference it as an early prototype trail. They will not run against the current venv unless reinstalled. This is intentional — they belong to the Phase 0 era.

---

## What this does *not* settle

- **Two utterances is not a benchmark.** The win is real on the audio we have; it is not yet WER-quantified on a labelled set. v1 of the eval (jiwer-based WER assertions on a 30+ utterance hand-labelled set) remains a follow-up.
- **CTC vs RNNT.** RNNT is the current default. CTC is faster (~75ms cheaper) but missed a nasal in TG-002 ("पैट" for "पैंट"). Worth re-running once we have ground truth.
- **Sarvam Saaras V3 oracle.** Not yet wired into the eval. One-shot API call against the same audio would give us an upper-bound reference.
- **Music Assistant + Home Assistant integration (Phase 4).** Decommission of Whisper has no bearing on this; deferred as planned.

---

## References

- `research/ab-results-2026-04-29.md` — the data
- `research/primer-gguf-pytorch-ollama-mlx.md` — the explanation for why MLX lost to Torch CPU
- `research/stt-ab-test-conformer-vs-whisper.md` — full discussion archive
- `prototype/stt_server.py` — the server in its post-decommission shape
- `~/Library/LaunchAgents/com.anchit.bhai-sunn-stt.plist` — the launchd manifest
- `eval/promptfooconfig.yaml` — the Promptfoo eval surface (to be updated to drop the Whisper provider in a follow-up commit)
