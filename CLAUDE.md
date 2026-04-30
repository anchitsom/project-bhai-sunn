# Project Bhai Sunn

**Status:** live — graduated to products on 2026-04-30. STT path benchmarked, IndicConformer 600M shipped under launchd, Promptfoo eval surface working. Wake-word, LLM, and TTS phases pending.
**Path:** `projects/products/project-bhai-sunn` (gitignored at agent-brain root; this folder IS the public repo at github.com/anchitsom/project-bhai-sunn)
**Collaborators:** joint project between Anchit Som and Adamya Tripathi

## Purpose
Hindi-first, fully open-source alternative to Alexa for Indian households. Edge satellites speak to a homelab brain. No cloud dependency in the core path.

## Architecture Decision
Two-node split, not on-device monolith. Cheap satellite (Pi 5, Pi Zero 2 W, ESP32 with OHF Voice firmware) handles wake-word and audio I/O. Mac Studio M1 Max in homelab handles STT, LLM, TTS. Wyoming protocol (Home Assistant's voice-pipeline contract) is the wire between them. Decision driven by the asymmetry: a bigger STT model and a bigger LLM make a real Hindi-quality difference; the satellite hardware does not.

Reasoning per [[platform-lock-in]] and [[vendor-lock-in]] in the wiki: defeating Alexa's lock-in requires interoperability and local-ai. Wyoming + open weights + open TTS satisfies this.

## Core Stack
- **Wake:** [[micro-wake-word]] (OpenHomeFoundation), custom-trained "Bhai Sunn" model, ~5 MB footprint, runs on satellite
- **STT:** AI4Bharat IndicConformer 600M (RNNT decoder), MIT licence, 22 Indian languages. Promoted on 2026-04-30 after the A/B in `research/ab-results-2026-04-29.md`. mlx-whisper decommissioned (preserved at git commit 80145e3 on the public repo if needed).
- **LLM:** Gemma 2 9B q4_K_M for Hindi-quality responses (multilingual, instruct-tuned). Falls back to Gemma 2 2B for the on-device-only build.
- **TTS:** Piper hi_IN-pratham-medium for v1. Swap to NeuTTS the moment a Hindi voice ships.
- **Protocol:** Wyoming (the same wire Home Assistant Voice uses). Decouples mic from brain; any Wyoming-speaking satellite plugs in.

## Always-on STT Service
- launchd plist: `~/Library/LaunchAgents/com.anchit.bhai-sunn-stt.plist` (committed to repo at `deploy/`)
- Wrapper: `~/services/bhai-sunn-stt/start.sh` (committed to repo at `deploy/`)
- Logs: `~/services/bhai-sunn-stt/{stdout,stderr}.log`
- Endpoint: `POST http://127.0.0.1:8765/transcribe` (localhost-only, no auth)
- Offline mode: plist sets `HF_HUB_OFFLINE=1` and `TRANSFORMERS_OFFLINE=1`. Once the model is cached the HF token can be rotated freely.
- Manage: `launchctl kickstart -k gui/$(id -u)/com.anchit.bhai-sunn-stt`

## Getting Started for Collaborators
This repo is set up so a fresh clone on a fresh Apple Silicon Mac becomes a working STT server plus a Promptfoo eval surface in well under an hour. Two runbooks cover the install end-to-end:
- `deploy/README.md` — the launchd service: dependencies, HF gate-acceptance, model pre-cache, plist install, verification
- `research/promptfoo-eval-setup.md` — the eval: how Promptfoo connects to the server, how to run, how to add new test cases, how to flip from compare-mode to WER-mode once a labelled set exists

For a one-screen rough order:
1. Clone the repo, `python3.13 -m venv .venv`, install Python deps (see `deploy/README.md` Step 1)
2. Accept the HF gate at the IndicConformer model page, generate a token, run `huggingface-cli login`
3. Pre-cache the model with one `from_pretrained` call (~3.4 GB download, only once)
4. Edit the path in `deploy/start.sh` to your local clone path, copy `start.sh` to `~/services/bhai-sunn-stt/`, copy the plist to `~/Library/LaunchAgents/`, `launchctl bootstrap`
5. `npm install -g promptfoo` (rebuild better-sqlite3 if Apple Silicon / Node-version mismatch)
6. From the project root, `promptfoo eval -c eval/promptfooconfig.yaml`, then `promptfoo view`

Test fixtures live in `fixtures/audio/`. Drop `.oga` or `.wav` audio there with stable filenames and reference them from `eval/promptfooconfig.yaml` to add new comparison rows.

The behavioural rule for AI assistants in this repo: if a Telegram voice note arrives, auto-transcribe via the running STT server and reply with the transcript. No need to ask each time. Saved as a global memory in `feedback_telegram_voice_auto_transcribe.md`.

## Status Tracker
- 2026-04-29: project created. Vision, architecture, bootstrap drafted.
- 2026-04-29: Phase 0 STT smoke test running. mlx-whisper large-v3-turbo on Mac Studio: 540ms warm latency for a 2.1s Hindi utterance. Persistent FastAPI STT server live on 127.0.0.1:8765.
- 2026-04-29: Hindi STT model survey (research/hindi-stt-models-2026-04-29.md). IndicConformer 600M selected as the A/B candidate against Whisper. indic-seamless rejected on CC BY-NC licence. Sarvam Saaras V3 / Gemini 3 Pro classed as oracle-only.
- 2026-04-29: A/B harness in flight. IndicConformer integration blocked on HuggingFace gate; Promptfoo eval config and brain endpoint scaffolded for plug-in once the model is available.
- 2026-04-29 (late): HF gate accepted. First A/B run on two Telegram voice notes. IndicConformer beats Whisper on aspiration ("भाई" vs Whisper's "बाई"), proper-noun recognition ("अदम्या" vs Whisper's hallucinated "अदम्यागी"), and latency (3x faster on the same Mac).
- 2026-04-30: IndicConformer 600M (RNNT) promoted to default STT. Whisper decommissioned. Server now runs under launchd as `com.anchit.bhai-sunn-stt` on 127.0.0.1:8765, KeepAlive=true. Telegram voice notes auto-transcribe via this endpoint going forward.
- 2026-04-30 (later): project graduated to products. Folder moved from `experiments/project-bhai-sunn_asp/` to `products/project-bhai-sunn/`. launchd plist + venv shebangs updated to the new path. Promptfoo eval rewired to `fixtures/audio/` relative paths. Collaborator runbook (`deploy/install.sh` per-user installer + `research/promptfoo-eval-setup.md`) shipped.

## Key Files
- `vision.md` — what this is, why it exists, against-Alexa positioning, Hindi-first wedge
- `architecture.md` — edge-brain split, Wyoming protocol flow, RAM budget on both sides, Mermaid + ASCII diagrams
- `README.md` — entry point
- `bootstrap.md` — install steps for the brain (Mac Studio) and a Pi satellite, end to end
- `prototype/test_pipeline.py` — Phase-0 mlx-whisper smoke test (decommissioned; preserved for history)
- `prototype/transcribe_voice_note.py` — Phase-0 raw-vs-denoised offline transcription (decommissioned; preserved for history)
- `prototype/stt_server.py` — persistent FastAPI server hosting IndicConformer 600M (RNNT default, CTC optional). ffmpeg-piped numpy, edge-silence trim, ~150-180ms warm STT. **The canonical STT path.**
- `deploy/` — launchd plist, wrapper script, install runbook
- `eval/promptfooconfig.yaml` — Promptfoo eval: Conformer RNNT vs CTC, compare-mode v0
- `fixtures/audio/` — test audio fixtures referenced by the eval (committed)
- `research/hindi-stt-models-2026-04-29.md` — verified survey of Hindi ASR options
- `research/stt-ab-test-conformer-vs-whisper.md` — full discussion of the A/B test design and interim findings
- `research/ab-results-2026-04-29.md` — the actual A/B data (Conformer wins on aspiration, proper-noun, latency)
- `research/decommission-mlx-whisper-2026-04-30.md` — formal decommission log
- `research/primer-gguf-pytorch-ollama-mlx.md` — runtime-stack explainer (PyTorch, GGUF, Ollama, MLX)
- `research/promptfoo-eval-setup.md` — how the Promptfoo eval is wired and how to extend it

## Open Questions
- Wake-word data collection: how many speakers, how many environments, synthetic data via Piper for augmentation
- Whether to use Wyoming-Satellite (Python) or build a custom satellite client. Wyoming-Satellite is the standard but heavier
- Music Assistant + Home Assistant integration: in scope for v2, not v1. v1 is a closed conversation loop, not a smart home controller
- Naming: "Bhai Sunn" is two phonemes — micro-wake-word benchmarks suggest 3+ syllables train more reliably. May need to test "Bhaiya Sunn" as alternate
- GitHub repo: deferred. Project lives locally first; public repo when v1 demo runs

## Related
- [[platform-lock-in]] — the wiki's framing; Alexa is the textbook example; the response is interoperability + local-ai
- [[vendor-lock-in]] — proprietary APIs / data gravity / integrated ecosystems; Wyoming + open weights breaks all three
- [[local-llm-project]] — same orchestrator-worker, simplicity-first stance applies here
- [[mac-studio-setup]] — the brain runs on this box; pipeline-api / Ollama / launchd patterns reused
- [[home-assistant]] — Wyoming is HA's protocol; v2 integration target
- [[neutts]] — replacement TTS path once Hindi voice ships
