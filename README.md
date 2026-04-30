# Bhai Sunn

A Hindi-first, fully open-source voice assistant for Indian households. Runs on hardware you own. No cloud in the core path.

> *Bhai* = brother. *Sunn* = listen. The register a household actually uses, not the imported corporate vocative of "Alexa".

## What this is

A two-node voice assistant:
- **Edge satellite** (Pi 5 / Pi Zero 2 W / ESP32) sits in a room with a mic and speaker. Runs custom wake-word detection.
- **Homelab brain** (Mac Studio M1 Max in this build) does STT, LLM, and TTS.
- They talk over the **Wyoming protocol** — Home Assistant's open audio-streaming wire format — over the home LAN.

Built as the answer to platform lock-in in the household-assistant category. Alexa is the textbook case of vendor lock-in (proprietary skills, integrated ecosystem, household data gravity); the prescription per the wiki is interoperability and local AI, which is exactly what this stack is.

## Status

Aspirational. Vision and architecture are written; no code yet, no hardware provisioned, no wake-word trained. Phase 0 (single-script smoke test on Mac Studio) is the next move.

## Read order

1. `vision.md` — what this is, why it exists, the wedge against Alexa
2. `architecture.md` — edge-brain split, RAM budgets, Mermaid diagrams, trade-off tables
3. `bootstrap.md` — install steps for brain and satellite, end-to-end
4. `prototype/test_pipeline.py` — Phase 0 smoke test
5. `CLAUDE.md` — project decisions, status tracker, open questions

## Stack

| Layer | Choice | Where it runs |
|---|---|---|
| Wake | micro-wake-word (custom "Bhai Sunn") | Satellite |
| STT | AI4Bharat IndicConformer 600M (RNNT) | Brain |
| LLM | Gemma 2 9B q4_K_M via Ollama | Brain |
| TTS | Piper hi_IN-pratham-medium | Brain |
| Wire | Wyoming protocol over LAN | Both |

The STT choice was settled by an A/B against Whisper large-v3-turbo (see `research/ab-results-2026-04-29.md` and `research/decommission-mlx-whisper-2026-04-30.md`). IndicConformer wins on aspiration, proper nouns, and latency on the same Mac Studio. Eval surface for the project is Promptfoo (`eval/promptfooconfig.yaml`).

## Why split

A monolithic Pi-only build fits in ~3 GB resident, but Hindi quality is materially better with a bigger ASR model (IndicConformer 600M) and a bigger LLM (Gemma 2 9B), both of which the Mac Studio runs comfortably. The satellite is therefore deliberately thin (~300 MB resident) so any cheap device can fill the role.

## Phased delivery

- **Phase 0** — single-script smoke test: record 5 s, transcribe, ask LLM, speak reply
- **Phase 1** — Wyoming server on Mac Studio + Wyoming satellite on Pi 5 with stock wake-word
- **Phase 2** — custom "Bhai Sunn" wake-word
- **Phase 3** — household policy file, personalised replies
- **Phase 4** — Music Assistant + Home Assistant integration

Phases 0 to 2 are v1.

## Non-goals (v1)

- Not a smart home controller (Home Assistant)
- Not a music streamer (Music Assistant)
- Not a frontier general assistant — v1 matches Alexa's actual usage envelope (timers, weather, lists, news, factoid lookup), not GPT-4 reasoning

## Source links

- micro-wake-word: https://github.com/OHF-Voice/micro-wake-word
- Music Assistant voice support: https://github.com/music-assistant/voice-support
- Wyoming / Home Assistant Voice: https://www.home-assistant.io/voice_control/
