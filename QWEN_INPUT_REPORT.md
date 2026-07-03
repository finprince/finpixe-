# QWEN INPUT REPORT

## 1. Image Format Sent to Qwen
- **Image Type:** Qwen receives the **FULL PAGE** rendered PNG image encoded as a Base64 JPEG string (size ~1.01 MB).
- **Stitched crops or Table crops:** No. Stitched, table, or field-level crops are not sent.
- **Resolution:** `1567x2150` pixels.
- **Calling Function:** `QwenProvider.call_single()` in `core/providers/qwen_provider.py` at line 702.

## 2. Request Metadata
- **Model:** `qwen2.5vl:7b`
- **API Base:** `http://localhost:11434/v1`
- **Temperature:** `0.0` (forced deterministic)
- **Prompt Size:** 2,324 characters (inclusive of the 1,035 characters of OCR text).
