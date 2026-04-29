# Project Bhai Sunn

**Status:** aspirational — design-stage, no code yet
**Graduates to:** products (when v1 satellite + brain demo runs end to end)

## Purpose
Hindi-first, fully open-source alternative to Alexa for Indian households. Edge satellites speak to a homelab brain. No cloud dependency in the core path.

## Architecture Decision
Two-node split, not on-device monolith. Cheap satellite (Pi 5, Pi Zero 2 W, ESP32 with OHF Voice firmware) handles wake-word and audio I/O. Mac Studio M1 Max in homelab handles STT, LLM, TTS. Wyoming protocol (Home Assistant's voice-pipeline contract) is the wire between them. Decision driven by the asymmetry: bigger Whisper and bigger LLM make a real Hindi-quality difference; the satellite hardware does not.

Reasoning per [[platform-lock-in]] and [[vendor-lock-in]] in the wiki: defeating Alexa's lock-in requires interoperability and local-ai. Wyoming + open weights + open TTS satisfies this.

## Core Stack
- **Wake:** [[micro-wake-word]] (OpenHomeFoundation), custom-trained "Bhai Sunn" model, ~5 MB footprint, runs on satellite
- **STT:** mlx-whisper, large-v3-turbo (per `feedback_mlx_whisper_apple_silicon.md` memory — faster-whisper is CPU-only on Mac and 10x slower)
- **LLM:** Gemma 2 9B q4_K_M for Hindi-quality responses (multilingual, instruct-tuned). Falls back to Gemma 2 2B for the on-device-only build.
- **TTS:** Piper hi_IN-pratham-medium for v1. Swap to NeuTTS the moment a Hindi voice ships.
- **Protocol:** Wyoming (the same wire Home Assistant Voice uses). Decouples mic from brain; any Wyoming-speaking satellite plugs in.

## Status Tracker
- 2026-04-29: project created. Vision and architecture drafted. No code yet. Wake-word training set not collected. Mac Studio brain services not running.

## Key Files
- `vision.md` — what this is, why it exists, against-Alexa positioning, Hindi-first wedge
- `architecture.md` — edge-brain split, Wyoming protocol flow, RAM budget on both sides, Mermaid + ASCII diagrams
- `README.md` — entry point
- `bootstrap.md` — install steps for the brain (Mac Studio) and a Pi satellite, end to end
- `prototype/test_pipeline.py` — minimal smoke test: record 5s, transcribe, ask LLM, speak reply

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
