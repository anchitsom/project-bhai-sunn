# Hindi Speech-to-Text Models: Verified Survey

**Compiled:** 2026-04-29
**Method:** Direct WebFetch on model cards and provider docs, plus targeted WebSearch. Earlier Gemini-CLI-driven version of this doc fabricated a non-existent "IndicWhisper v2"; this version is grounded in actual sources cited per claim.

---

## TL;DR for Bhai Sunn

| Model | Verdict for project |
|---|---|
| **Whisper large-v3-turbo** | Stay on this. MIT licence, native MLX support on Apple Silicon, strong general Hindi. Current production. |
| **AI4Bharat IndicConformer 600M** | A/B candidate. MIT licence, 22 Indian languages, hybrid CTC+RNNT. Worth running same audio against. No native MLX, needs ONNX runtime. |
| **AI4Bharat indic-seamless (2B)** | **Reject.** Licence is CC BY-NC 4.0 — non-commercial. Breaks vision.md's open-source thesis. |
| **Sarvam Saaras V3** | API-only, proprietary. Reject as production path. Useful as a quality oracle: call it once on our test set to bound how much we're losing by going local. |
| **Google Gemini 3 Pro / Chirp** | API-only, proprietary. Same role as Sarvam — oracle, not production. |

---

## Open-Weight Candidates

### 1. Whisper large-v3-turbo (current default)

- **Source:** [openai/whisper-large-v3-turbo on HuggingFace](https://huggingface.co/openai/whisper-large-v3-turbo)
- **Licence:** MIT
- **Architecture:** Whisper large-v3 with decoder pruned from 32 to 4 layers
- **Parameters:** 809M (per OpenAI release notes for the turbo variant)
- **Hindi WER:** not separately published in the model card. FLEURS-overall is reported as ~10% across 102 languages (no Hindi-specific number)
- **Mac runtime:** native MLX via `mlx-community/whisper-large-v3-turbo`
- **Trade-off:** "way faster, at the expense of a minor quality degradation" (model card)

### 2. AI4Bharat IndicConformer 600M Multilingual

- **Source:** [ai4bharat/indic-conformer-600m-multilingual on HuggingFace](https://huggingface.co/ai4bharat/indic-conformer-600m-multilingual)
- **Licence:** MIT
- **Architecture:** Multilingual Conformer-based hybrid CTC + RNNT
- **Parameters:** 600M
- **Languages:** 22 official Indian languages (IN-22), including Hindi
- **Inference:** transformers + torchaudio + onnxruntime; supports both CTC and RNNT decoding from the same forward pass
- **Hindi WER:** not in model card. AI4Bharat references VISTAAR / IndicSUPERB / Lahaja / Svarah benchmarks but does not publish per-language WER on the public model card; needs paper dive
- **Mac runtime:** ONNX runtime path is the documented one; no native MLX wrapper today
- **Notes:** positioned as "the country's first open-source ASR system" covering 22 Indian languages

### 3. AI4Bharat indic-seamless (the user's link)

- **Source:** [ai4bharat/indic-seamless on HuggingFace](https://huggingface.co/ai4bharat/indic-seamless)
- **Licence:** **CC BY-NC 4.0 (Creative Commons Attribution-NonCommercial)**
- **Architecture:** SeamlessM4T-v2 fine-tuned for Indian languages
- **Parameters:** 2B
- **Languages:** 13 Indian languages
- **Tasks:** ASR + speech-to-text translation
- **Released:** November 2024 (arxiv 2411.04699)
- **Training data:** BhasaAnuvaad, NPTEL, IndicVoices-ST, Mann-ki-Baat
- **Claim:** "Achieves SOTA on FLEURS dataset for Hindi" (no specific WER in card)
- **Verdict:** licence breaks vision.md ("Hindi-first, fully open-source"). CC BY-NC means anyone forking the project for Marathi or Bhojpuri or commercial use cannot legally use this model. Hard rejection.

---

## API-Only Candidates (oracles, not production)

### 4. Sarvam Saaras V3

- **Source:** [Saaras V3 launch post on sarvam.ai](https://www.sarvam.ai/blogs/asr) (published 2026-02-10)
- **Languages:** 23 (22 official Indian + English)
- **Training data:** 1 million+ hours
- **IndicVoices WER:** 19.31% on top-10 languages subset (includes Hindi)
- **Predecessor (Saaras V2.5):** ~22% WER on the same set
- **Comparison claim:** Sarvam reports beating GPT-4o Transcribe, Gemini 3 Pro, Deepgram Nova3, ElevenLabs Scribe v2 on IndicVoices, without publishing the competitor numbers in the post
- **Streaming support:** yes, V3 added streaming transcription
- **Saarika V2.5 (predecessor, deprecated):** VISTAAR Hindi CER 4.42%, overall WER 18.32% across all 11 languages, per [Sarvam docs](https://docs.sarvam.ai/api-reference-docs/getting-started/models/saarika)
- **Deployment:** API only, proprietary

### 5. Google Gemini 3 Pro / 2.5 Native Audio

- **Source:** [Artificial Analysis ASR leaderboard](https://artificialanalysis.ai/speech-to-text)
- **Reported AA-WER:** 2.9% on AgentTalk / VoxPopuli / Earnings22 (English-heavy, not Hindi)
- **Hindi specific:** Gemini supports Hindi audio input; no public Hindi WER number from Google
- **Deployment:** API only

### 6. Google Chirp 3 / Universal Speech Model

- **Source:** Google Cloud STT documentation
- **Languages:** broad, including Hindi
- **Hindi WER:** not separately published

---

## What the earlier Gemini-CLI survey got wrong

The earlier version of this document (replaced by this one in the same git commit history) was generated by Gemini CLI and contained at least these specific fabrications:

- **"IndicWhisper v2 (1.55B params, 5.3% FLEURS Hindi WER)"** — does not exist. AI4Bharat ships IndicWhisper (v1, original release) and the newer flagship is IndicConformer 600M, not a "v2" of IndicWhisper.
- **"NVIDIA Neotron Speech, CES 2026"** — no such product release found in any source.
- **Specific WER percentages in the comparison table** (Sarvam Saaras v3 25.8% Vaani, IndicWhisper v2 8.8% Kathbath, etc.) — not corroborated by any first-party source. Sarvam's own published number on IndicVoices is 19.31% for the top-10 languages subset; the previous table's numbers should not be relied on.

The general memory rule applies: Gemini hallucinates model versions and benchmark percentages with high confidence. Use direct fetches against primary sources (model cards, provider blogs, papers) for any decision-load-bearing fact.

---

## Recommendation for Bhai Sunn

1. **Stay on Whisper large-v3-turbo for v1.** It's working, MIT-licensed, native MLX on Apple Silicon, and the existing pipeline already hits the 540ms latency target.

2. **Add IndicConformer 600M as the first A/B candidate.** Same audio, same evaluation harness, two outputs. AI4Bharat's positioning is exactly aligned with the vision (Indian-language-native, open weights, 22 languages). The licence is MIT, so we're not trading sovereignty for accuracy. The runtime gap (no native MLX) is solvable with ONNX.

3. **Use Sarvam Saaras V3 as a quality oracle, not a production path.** One API call against our evaluation set tells us how much accuracy we're sacrificing by being local. If the gap is small, we stay local; if it's huge, we re-examine the local-first thesis. Either way, the API stays out of the production wire.

4. **Skip indic-seamless entirely.** CC BY-NC 4.0 is incompatible with vision.md. The 2B model with claimed FLEURS-Hindi SOTA is real, but a non-commercial licence on a "fully open-source alternative to Alexa for Indian households" is a contradiction.

5. **Defer Gemini / Chirp evaluation.** No published Hindi WER, API-only, and the project's whole point is not to send household audio to Google. They'd only be useful as comparison baselines at the same time as Sarvam — a single oracle pass, not a production option.

---

## Sources

- [openai/whisper-large-v3-turbo on HuggingFace](https://huggingface.co/openai/whisper-large-v3-turbo)
- [ai4bharat/indic-conformer-600m-multilingual on HuggingFace](https://huggingface.co/ai4bharat/indic-conformer-600m-multilingual)
- [ai4bharat/indic-seamless on HuggingFace](https://huggingface.co/ai4bharat/indic-seamless)
- [AI4Bharat ASR area page](https://ai4bharat.iitm.ac.in/areas/asr)
- [Saaras V3 launch blog, sarvam.ai](https://www.sarvam.ai/blogs/asr)
- [Saarika V2.5 docs, sarvam.ai](https://docs.sarvam.ai/api-reference-docs/getting-started/models/saarika)
- [Artificial Analysis ASR leaderboard](https://artificialanalysis.ai/speech-to-text)
