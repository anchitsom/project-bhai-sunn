# Deploy: bhai-sunn STT launchd service

Reproducible deployment of the STT server as a macOS launchd agent. Tested on macOS 14+ with Apple Silicon (M1 Max).

## What's here

- `com.anchit.bhai-sunn-stt.plist` — launchd manifest. Reads from `~/services/bhai-sunn-stt/start.sh`. Sets `PATH`, `HF_HOME`, `HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1`. KeepAlive=true.
- `start.sh` — wrapper that cd's into the project, then exec's `uvicorn prototype.stt_server:app` from the project venv on `127.0.0.1:8765`.

## Install

```bash
# 1. Make sure the project venv is set up and the model is cached
cd /Users/anchitsom/agent-brain/projects/experiments/project-bhai-sunn_asp
python3.13 -m venv .venv
.venv/bin/pip install fastapi uvicorn transformers torch torchaudio onnxruntime onnx librosa soundfile

# 2. Authenticate to HuggingFace once and accept the IndicConformer gate at
# https://huggingface.co/ai4bharat/indic-conformer-600m-multilingual
.venv/bin/python -c "from huggingface_hub import login; login(token='hf_...')"

# 3. Pre-cache the model (first run downloads ~3.4 GB)
.venv/bin/python -c "from transformers import AutoModel; AutoModel.from_pretrained('ai4bharat/indic-conformer-600m-multilingual', trust_remote_code=True)"

# 4. Install the wrapper script
mkdir -p ~/services/bhai-sunn-stt
cp deploy/start.sh ~/services/bhai-sunn-stt/start.sh
chmod +x ~/services/bhai-sunn-stt/start.sh

# 5. Install the launchd plist
cp deploy/com.anchit.bhai-sunn-stt.plist ~/Library/LaunchAgents/

# 6. Bootstrap the service (loads + starts)
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.anchit.bhai-sunn-stt.plist

# 7. Verify
curl -s http://127.0.0.1:8765/health
```

Success: `{"warmed":true,"model":"ai4bharat/indic-conformer-600m-multilingual","default_decoder":"rnnt","default_language":"hi"}`.

## Manage

```bash
# Restart (after editing start.sh, plist, or the server code)
launchctl kickstart -k gui/$(id -u)/com.anchit.bhai-sunn-stt

# Stop
launchctl bootout gui/$(id -u)/com.anchit.bhai-sunn-stt

# Inspect
launchctl print gui/$(id -u)/com.anchit.bhai-sunn-stt | head

# Logs
tail -f ~/services/bhai-sunn-stt/stderr.log
```

## Token rotation

The service runs in offline mode (`HF_HUB_OFFLINE=1`), so the HuggingFace token in `~/.cache/huggingface/token` is *not* required for the server to keep running. Rotate freely:

1. Revoke the old token at https://huggingface.co/settings/tokens
2. (Optional) `rm ~/.cache/huggingface/token ~/.cache/huggingface/stored_tokens`
3. The service is unaffected. A new token is only required to download a new model or update an existing one.

## Why localhost-only

The service exposes no auth. The bind-host rule for the homelab is "0.0.0.0 only when the service has auth or is read-only". Pinning to `127.0.0.1` keeps the wire trusted-loopback. Registered in `system/services-and-ports.md` under Localhost-only.
