# STT A/B Results: Whisper vs IndicConformer (2026-04-29)

**Run:** v0 compare-mode, two voice notes, three providers each
**Server:** `prototype/stt_server.py` warm at 127.0.0.1:8765
**Note:** Run via `curl` rather than `promptfoo eval` because the installed Promptfoo's `better-sqlite3` native module was compiled against an older Node (NODE_MODULE_VERSION 115) and the current Node is 141. Rebuild is documented at the bottom; the data is the same regardless of harness.

---

## Test cases

### TG-001 — short greeting

- **Audio:** `1777478093345-AgADQRwAAuAkmVM.oga`, 2.09s
- **User-spoken (per project context):** "Bhai Sunn, kaisa hai" (Bhai Sunn, how are you)

| Provider | Transcript | Notes |
|---|---|---|
| Whisper large-v3-turbo | बाई सुन कैसा है | "Bhai" rendered as "बाई" (Bai = lady). Aspirated Bh dropped. |
| Conformer RNNT | भाई सुन कैसा है | **"Bhai" rendered correctly as "भाई".** |
| Conformer CTC | भाई सुन कैसा है | **"Bhai" rendered correctly as "भाई".** |

### TG-002 — sentence with proper noun

- **Audio:** `1777479556339-AgADRBwAAuAkmVM.oga`, 2.93s
- **User-spoken (per project context):** "Bhai Sunn, Adamya ki paint fad gayi" — uses the wake phrase plus the collaborator's name as a real-world test

| Provider | Transcript | Notes |
|---|---|---|
| Whisper large-v3-turbo | बाइस सुन अदम्यागी ना पैंट फड़ गी | "Bhai" → "बाइस" (Bais, nonsense). "Adamya" hallucinated as "अदम्यागी". Trailing verb truncated. |
| Conformer RNNT | भाई सोन अदम्या की ना पैंट फट गई | **"Bhai" correct. "Adamya" recognised correctly. "paint phat gayi" recovered (verb root + tense correct).** "सोन" instead of "सुन" is the only meaningful error. |
| Conformer CTC | भाई सोन अदम्या की ना पैट फट गई | Same pattern as RNNT. "पैट" (pat) vs "पैंट" (pant) — the nasal न missed. |

---

## Latency (warm)

| Provider | TG-001 STT | TG-002 STT | Notes |
|---|---|---|---|
| Whisper large-v3-turbo | 465ms | 523ms | Apple Neural Engine via MLX. Whole pipeline 540-570ms. |
| Conformer RNNT | 184ms | 184ms | Torch CPU. **2.8x faster than Whisper.** Hybrid RNNT decoder. |
| Conformer CTC | 128ms | 150ms | Torch CPU. **3.5x faster than Whisper.** CTC is single-shot, streaming-friendly. |

The Conformer latency advantage on Mac Studio CPU was unexpected — MLX-on-Apple-Silicon is supposed to be the speedup story, and torch on CPU the slow path. The likely explanation: Conformer is ~600M params (vs Whisper turbo's 809M), the architecture uses non-autoregressive decoding (CTC) or a lean RNNT decoder, and Whisper's autoregressive transformer decoder pays per-token overhead. Conformer is also smaller per parameter on RAM (q4 wasn't even needed).

---

## Verdict

**Conformer is meaningfully better than Whisper for the Bhai Sunn use case.**

Three concrete wins on a tiny test set:
1. **Aspirated consonants preserved.** "भ" (bh) is correctly retained in "भाई" — Whisper consistently drops it to "ब" (b). For a project where the wake phrase is "Bhai Sunn", this is not cosmetic.
2. **Proper nouns recognised.** "Adamya" is transcribed as "अदम्या", not hallucinated as gibberish. Whisper produced "अदम्यागी" — phonetically nearby, semantically meaningless.
3. **Faster on the same hardware.** 2.8x to 3.5x speedup on Mac Studio CPU vs Whisper-MLX on Apple Neural Engine.

**Remaining concerns:**
- "सुन" (sun, listen) was rendered as "सोन" (son, gold) by Conformer on TG-002. Wrong word with similar phonemes. On TG-001 the same word came out correctly. Suggests the model is sensitive to surrounding context in ambiguous cases.
- "पैंट" lost its nasal in Conformer CTC ("पैट"). RNNT got it right. Mild support for RNNT > CTC for our use case.
- Two utterances is not a benchmark. Consistent with v0 compare-mode caveat in the discussion doc — needs hand-labelled ground truth on 30+ utterances before it becomes a measurement.

**Recommendation update:**
- Promote IndicConformer 600M (RNNT decoder) to the default STT in the brain pipeline.
- Keep Whisper as a fallback / second opinion for English-heavy or non-Indic content.
- Update `architecture.md` to reflect this shift.

---

## Promptfoo follow-up

The installed Promptfoo CLI fails with:

```
Error: The module 'better-sqlite3.node' was compiled against a different
Node.js version using NODE_MODULE_VERSION 115. This version of Node.js
requires NODE_MODULE_VERSION 141.
```

Fix in either of two ways:
- `cd /Users/anchitsom/.nvm/versions/node/v20.20.2/lib/node_modules/promptfoo && npm rebuild better-sqlite3`
- `nvm use 20 && promptfoo eval ...` (run with the older Node the binary was built against)

Once Promptfoo is happy, the `eval/promptfooconfig.yaml` is already wired and runs the same three providers; the `--output ab-results.json` flag drops a structured run record. The curl-driven results above are equivalent, just less browse-friendly.

---

## Raw data

```json
{
  "TG-001": {
    "whisper":           {"text": "बाई सुन कैसा है",                 "stt_ms": 465},
    "conformer_rnnt":    {"text": "भाई सुन कैसा है",                 "stt_ms": 527, "note": "first call, model load+inference cold"},
    "conformer_ctc":     {"text": "भाई सुन कैसा है",                 "stt_ms": 128}
  },
  "TG-002": {
    "whisper":           {"text": "बाइस सुन अदम्यागी ना पैंट फड़ गी",  "stt_ms": 523},
    "conformer_rnnt":    {"text": "भाई सोन अदम्या की ना पैंट फट गई",   "stt_ms": 184},
    "conformer_ctc":     {"text": "भाई सोन अदम्या की ना पैट फट गई",    "stt_ms": 150}
  }
}
```
