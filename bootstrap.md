# Bootstrap: Bhai Sunn

**Status:** v0.1, 2026-04-29
**Reads first:** architecture.md
**Reads next:** prototype/test_pipeline.py

This guide takes a fresh Mac Studio and a fresh Pi to a working Phase 1 voice loop. Phase 0 (single-script smoke test) is at the end and runs on the Mac Studio alone.

## Prerequisites

- Mac Studio M1 Max with macOS 14+ and Homebrew installed
- A Pi 5 (8GB recommended) on the same LAN, running Pi OS 64-bit
- A USB microphone and powered speaker on the Pi (or a ReSpeaker HAT)
- SSH access to the Pi

## Phase 0: Mac Studio smoke test

Goal: prove the full audio loop on the brain alone, no satellite. Records a 5-second clip from the Mac's mic, transcribes it, sends to the LLM, speaks the reply.

### Step 1: install brain dependencies

What: install mlx-whisper, Piper TTS, and pull the LLM into Ollama.
Why: these are the three brain services; we want them resident before any test.

```bash
# Use the Bash-tool-friendly PATH override; Homebrew binaries are not on Claude's default PATH
PATH="/opt/homebrew/bin:$PATH"

# mlx-whisper for Apple Silicon STT
pip install mlx-whisper

# Piper TTS via Homebrew (or pip if not available)
brew install piper-tts || pip install piper-tts

# Hindi voice for Piper
mkdir -p ~/.local/share/piper-voices
cd ~/.local/share/piper-voices
curl -L -O https://huggingface.co/rhasspy/piper-voices/resolve/main/hi/hi_IN/pratham/medium/hi_IN-pratham-medium.onnx
curl -L -O https://huggingface.co/rhasspy/piper-voices/resolve/main/hi/hi_IN/pratham/medium/hi_IN-pratham-medium.onnx.json

# Pull Gemma 2 9B into Ollama (already installed per mac-studio-setup)
ollama pull gemma2:9b
```

Success: `ollama list` shows `gemma2:9b`, the two Piper files exist, `python -c "import mlx_whisper"` returns no error.

### Step 2: run the smoke test

What: execute `prototype/test_pipeline.py`.
Why: end-to-end check that audio in produces audio out, in Hindi, on this machine alone.

```bash
cd ~/agent-brain/projects/experiments/project-bhai-sunn_asp
python prototype/test_pipeline.py
```

Success: the script prompts you to speak in Hindi, captures 5 seconds, prints the transcription, prints the LLM's reply text, and plays the spoken reply through the Mac's speakers within ~5 seconds total wall-clock.

If success: Phase 0 complete. Move to Phase 1.

## Phase 1: Wyoming server on Mac, Wyoming satellite on Pi

Goal: replace the single-script demo with a long-running brain service the Pi satellite can call.

### Step 3: install Wyoming services on Mac Studio

What: install three Wyoming wrappers — one each for whisper, piper, and a "wyoming-llm" shim for Ollama.
Why: the Wyoming protocol is the wire; each model needs a Wyoming-speaking process the gateway can route to.

```bash
PATH="/opt/homebrew/bin:$PATH"

pip install wyoming wyoming-faster-whisper wyoming-piper

# wyoming-faster-whisper supports MLX backend via env var
WYOMING_WHISPER_BACKEND=mlx

# Note: as of 2026-04, wyoming-faster-whisper added MLX support behind WYOMING_WHISPER_BACKEND=mlx
# Verify the flag still exists; if not, fall back to mlx-whisper served via a thin Wyoming wrapper
```

Each service runs on a distinct port:
- wyoming-faster-whisper (MLX backend): `tcp://0.0.0.0:10300`
- wyoming-piper: `tcp://0.0.0.0:10200`
- wyoming-ollama (custom shim, see step 4): `tcp://0.0.0.0:10400`

Bind on `0.0.0.0` so the Pi satellite can reach the Mac on LAN. **Per `feedback_launchd_bind_host.md` memory: only bind 0.0.0.0 when the service has auth or is read-only.** Wyoming has no auth model. Mitigation: run only on the trusted LAN interface (Tailscale or LAN), not on a public network. Document this in `system/services-and-ports.md` when launchd plists are added.

### Step 4: write the Ollama shim

What: a small Python service that speaks Wyoming on one end and Ollama HTTP on the other.
Why: Wyoming has no native LLM concept (it was built for STT/TTS/wake); the brain pipeline needs a glue process.

The shim accepts a Wyoming "intent" event with the transcribed text, calls Ollama's `/api/chat` with the Gemma 2 9B model and a Hindi-leaning system prompt, and emits a Wyoming "tts-input" event with the reply text. Reference implementation: see `prototype/wyoming_ollama_shim.py` (to be written in Phase 1).

### Step 5: configure the Mac as a Wyoming "voice pipeline"

What: install Home Assistant in Docker on Mac Studio (or skip if already running on the homelab), point its Voice pipeline at the three Wyoming services.
Why: HA's Voice pipeline is the orchestrator that ties wake → STT → LLM → TTS together over Wyoming.

Alternative: skip Home Assistant entirely and write a thin `wyoming-pipeline` Python orchestrator in `prototype/`. Faster to iterate; loses the eventual HA integration path. Decision deferred — start with the standalone pipeline, swap to HA in Phase 4.

### Step 6: install Wyoming satellite on the Pi

What: install `wyoming-satellite` on the Pi, configure it to point at the Mac's Wyoming services on the LAN, set wake-word to a stock model (e.g. `ok_nabu` from `wyoming-openwakeword`).
Why: this is the off-the-shelf satellite client; it handles audio capture, wake detection, and streaming.

```bash
# On the Pi
sudo apt install python3-pip python3-venv portaudio19-dev libportaudio2
python3 -m venv ~/wyoming-venv
source ~/wyoming-venv/bin/activate
pip install wyoming-satellite wyoming-openwakeword

# Run the satellite
wyoming-satellite \
  --name 'kitchen-bhai-sunn' \
  --uri 'tcp://0.0.0.0:10700' \
  --mic-command 'arecord -r 16000 -c 1 -f S16_LE -t raw' \
  --snd-command 'aplay -r 22050 -c 1 -f S16_LE -t raw' \
  --wake-uri 'tcp://localhost:10500' \
  --wake-word-name 'ok_nabu'

# In a second shell: openwakeword Wyoming wrapper
pip install wyoming-openwakeword
wyoming-openwakeword --uri 'tcp://0.0.0.0:10500' --preload-model 'ok_nabu'
```

Success: say "ok nabu, what time is it" near the Pi's mic. The Pi forwards audio to the Mac, the Mac transcribes, the LLM replies, the Mac synthesises, the Pi plays it back.

If success: Phase 1 complete. Phase 2 swaps the wake-word.

## Phase 2: custom "Bhai Sunn" wake-word

### Step 7: collect or generate training data

What: build a labelled dataset of "Bhai Sunn" positives and ambient negatives.
Why: micro-wake-word needs both classes to avoid false positives.

Two paths:
1. **Synthetic-first** — use Piper to generate ~5,000 "Bhai Sunn" samples in varied voices and speeds. Get a working v0 model in hours.
2. **Real-first (recommended for production)** — collect ~500 real utterances from household members in real rooms, mix 70/30 with synthetic.

Negatives: 24 hours of household ambient audio (TV, kitchen sounds, conversation), labelled as "not-wake".

### Step 8: train the model

What: run micro-wake-word's training script on the labelled dataset.
Why: produces a TFLite Micro `.tflite` file that wyoming-microwakeword can load.

Pointer: https://github.com/OHF-Voice/micro-wake-word — see `training/` directory for the Colab-friendly notebook.

### Step 9: deploy

What: copy the `.tflite` model to the Pi, replace `wyoming-openwakeword` with `wyoming-microwakeword` pointing at the new model.
Why: this is what makes "Bhai Sunn" the actual wake phrase.

```bash
# On the Pi
pip install wyoming-microwakeword
wyoming-microwakeword --uri 'tcp://0.0.0.0:10500' --model /home/pi/bhai-sunn.tflite
```

Success: stock wake word stops working. "Bhai Sunn" wakes the assistant. Measure false-positive rate over 24 hours of normal household activity; iterate on dataset until under 2%.

## Failure modes and recovery

| Symptom | Likely cause | Fix |
|---|---|---|
| Wake fires constantly on TV audio | Insufficient negative training data | Re-train with more household-ambient negatives |
| Whisper returns English text for Hindi audio | Language code wrong | Pass `language='hi'` explicitly to mlx-whisper |
| LLM replies in English to Hindi prompts | System prompt is English | Set system prompt in Hindi or explicitly instruct Hindi response |
| Pi cannot reach Mac on LAN | mDNS / firewall / wrong bind | Check `lsof -iTCP:10300 -sTCP:LISTEN` on Mac; ping Mac IP from Pi |
| TTS sounds robotic / clipped | Piper "low" quality variant | Confirm `medium` model file is loaded |
| Latency over 5 seconds end to end | LLM cold-start or KV cache miss | Pre-warm Ollama with a dummy request at service start |

## What is deliberately deferred

- **launchd plists for the brain services.** Phase 1 runs them as foreground processes for visibility. Once the wire works, package them per the mac-studio-setup convention with explicit `PATH=/opt/homebrew/bin:...` (per the `feedback_launchd_path.md` memory).
- **Tailscale exposure.** v1 is LAN-only. Cross-network deployment via Tailscale is a Phase 4 concern.
- **Music Assistant + Home Assistant integration.** Phase 4. Not blocked by anything earlier.

## References

| File | Purpose |
|---|---|
| `architecture.md` | The diagrams and trade-offs this guide implements |
| `prototype/test_pipeline.py` | Phase 0 single-script smoke test |
| `~/agent-brain/projects/products/mac-studio-setup/` | launchd / service convention to follow when packaging |
| `~/agent-brain/system/services-and-ports.md` | Where to register the new ports |
