# Deploy: bhai-sunn STT launchd service

Reproducible deployment of the STT server as a macOS launchd agent. Tested on macOS 14+ with Apple Silicon (M1 Max).

## What's here

- `install.sh` — per-user installer. Generates a customised `start.sh` and plist for the current user (replaces the hard-coded paths in the canonical `start.sh` and `com.anchit.bhai-sunn-stt.plist` below). Run this rather than copying the canonical files when you set up on a new machine.
- `start.sh` — canonical wrapper. Reference copy of what the install script generates. Hard-codes Anchit's project path; do not copy directly.
- `com.anchit.bhai-sunn-stt.plist` — canonical launchd manifest. Reference copy. Same caveat.

## Install on a fresh machine

### Step 1: prerequisites

What: project venv set up, model cached locally.
Why: the launchd service runs in offline mode, so the model must already be on disk before it boots. The installer checks for both and refuses to install if either is missing.

```bash
cd <path to your clone of project-bhai-sunn>

# Python venv
python3.13 -m venv .venv
.venv/bin/pip install fastapi uvicorn transformers torch torchaudio onnxruntime onnx librosa soundfile

# Accept the gate at https://huggingface.co/ai4bharat/indic-conformer-600m-multilingual
# Generate a token at https://huggingface.co/settings/tokens
.venv/bin/python -c "from huggingface_hub import login; login(token='hf_...')"
chmod 600 ~/.cache/huggingface/token ~/.cache/huggingface/stored_tokens

# Pre-cache (~3.4 GB download, only once)
.venv/bin/python -c "from transformers import AutoModel; AutoModel.from_pretrained('ai4bharat/indic-conformer-600m-multilingual', trust_remote_code=True)"
```

### Step 2: install the launchd service

What: customise paths and labels for the current user, install plist + wrapper, bootstrap.
Why: the canonical files in this directory hard-code Anchit's home directory and label. The installer generates per-user copies.

```bash
./deploy/install.sh
```

The installer writes:
- `~/services/bhai-sunn-stt/start.sh` — your wrapper (correct path baked in)
- `~/Library/LaunchAgents/com.bhai-sunn.bhai-sunn-stt.plist` — your plist (correct paths and label)

It then `launchctl bootstrap`s the service and prints verification + management commands.

### Step 3: verify

```bash
curl -s http://127.0.0.1:8765/health
```

Success: `{"warmed":true,"model":"ai4bharat/indic-conformer-600m-multilingual","default_decoder":"rnnt","default_language":"hi"}`. First boot takes ~10-15 seconds while the model loads.

### Step 4: smoke-test a transcription

```bash
curl -s -X POST http://127.0.0.1:8765/transcribe \
  -H 'Content-Type: application/json' \
  -d '{"path": "fixtures/audio/tg-001-greeting.oga"}' | python3 -m json.tool
```

Success: `text: "भाई सुन कैसा है"`, `timings.stt` under 200ms.

## Manage

```bash
# Restart (after editing server code or the plist)
launchctl kickstart -k gui/$(id -u)/com.bhai-sunn.bhai-sunn-stt

# Stop
launchctl bootout gui/$(id -u)/com.bhai-sunn.bhai-sunn-stt

# Inspect
launchctl print gui/$(id -u)/com.bhai-sunn.bhai-sunn-stt | head

# Logs
tail -f ~/services/bhai-sunn-stt/stderr.log
```

(Anchit's existing install uses the older label `com.anchit.bhai-sunn-stt`; new installs from `install.sh` use `com.bhai-sunn.bhai-sunn-stt`. Substitute the right label in the commands above.)

## Token rotation

The service runs in offline mode (`HF_HUB_OFFLINE=1`), so the HuggingFace token in `~/.cache/huggingface/token` is *not* required for the server to keep running. Rotate freely:

1. Revoke the old token at https://huggingface.co/settings/tokens
2. (Optional) `rm ~/.cache/huggingface/token ~/.cache/huggingface/stored_tokens`
3. The service is unaffected. A new token is only required to download a *new* model or update an existing one.

## Why localhost-only

The service exposes no auth. The bind-host rule for the homelab is "0.0.0.0 only when the service has auth or is read-only". Pinning to `127.0.0.1` keeps the wire trusted-loopback. Anchit's local install is also registered in `<workspace>/system/services-and-ports.md` under Localhost-only.
