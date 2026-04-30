# Project Bhai Sunn

**Status:** aspirational — STT path benchmarked, brain services not yet packaged
**Graduates to:** products (when v1 satellite + brain demo runs end to end)
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
- launchd plist: `~/Library/LaunchAgents/com.anchit.bhai-sunn-stt.plist`
- Wrapper: `~/services/bhai-sunn-stt/start.sh`
- Logs: `~/services/bhai-sunn-stt/{stdout,stderr}.log`
- Endpoint: `POST http://127.0.0.1:8765/transcribe` (localhost-only, registered in `system/services-and-ports.md`)
- HF auth: persisted at `~/.cache/huggingface/token` (mode 600); the plist sets `HF_HOME` so the cached token is found without env-var passthrough
- Manage: `launchctl kickstart -k gui/$(id -u)/com.anchit.bhai-sunn-stt`

## Status Tracker
- 2026-04-29: project created. Vision, architecture, bootstrap drafted.
- 2026-04-29: Phase 0 STT smoke test running. mlx-whisper large-v3-turbo on Mac Studio: 540ms warm latency for a 2.1s Hindi utterance. Persistent FastAPI STT server live on 127.0.0.1:8765.
- 2026-04-29: Hindi STT model survey (research/hindi-stt-models-2026-04-29.md). IndicConformer 600M selected as the A/B candidate against Whisper. indic-seamless rejected on CC BY-NC licence. Sarvam Saaras V3 / Gemini 3 Pro classed as oracle-only.
- 2026-04-29: A/B harness in flight. IndicConformer integration blocked on HuggingFace gate; Promptfoo eval config and brain endpoint scaffolded for plug-in once the model is available.
- 2026-04-29 (late): HF gate accepted. First A/B run on two Telegram voice notes. IndicConformer beats Whisper on aspiration ("भाई" vs Whisper's "बाई"), proper-noun recognition ("अदम्या" vs Whisper's hallucinated "अदम्यागी"), and latency (3x faster on the same Mac).
- 2026-04-30: IndicConformer 600M (RNNT) promoted to default STT. Whisper decommissioned. Server now runs under launchd as `com.anchit.bhai-sunn-stt` on 127.0.0.1:8765, KeepAlive=true. Telegram voice notes auto-transcribe via this endpoint going forward.

## Key Files
- `vision.md` — what this is, why it exists, against-Alexa positioning, Hindi-first wedge
- `architecture.md` — edge-brain split, Wyoming protocol flow, RAM budget on both sides, Mermaid + ASCII diagrams
- `README.md` — entry point
- `bootstrap.md` — install steps for the brain (Mac Studio) and a Pi satellite, end to end
- `prototype/test_pipeline.py` — minimal one-shot smoke test (record 5s, transcribe, ask LLM, speak reply)
- `prototype/transcribe_voice_note.py` — A/B raw-vs-denoised offline transcription
- `prototype/stt_server.py` — persistent FastAPI server hosting IndicConformer 600M (RNNT default, CTC optional). ffmpeg-piped numpy, edge-silence trim, ~150-180ms warm STT.
- `research/hindi-stt-models-2026-04-29.md` — verified survey of Hindi ASR options (Whisper, IndicConformer, indic-seamless, Sarvam, Gemini, Chirp) with sources cited per claim
- `research/stt-ab-test-conformer-vs-whisper.md` — full discussion of the A/B test design, Promptfoo wiring, interim findings
- `eval/` — Promptfoo eval config for Whisper-vs-Conformer A/B

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
