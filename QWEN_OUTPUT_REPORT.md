# QWEN OUTPUT REPORT

## 1. Raw Qwen Response
Response from Ollama model `qwen2.5vl:7b`:
- **Latency:** 146.42s
- **Prompt Tokens:** 4,845
- **Completion Tokens:** 1,243
- **Total Tokens:** 6,088
- **Extracted JSON:** (Refer to QWEN_OUTPUT_REPORT.md / FINAL_OCR_QWEN_FORENSIC_REPORT.md)

## 2. OCR Text vs Qwen Interpretation
- **Invoice Number:** OCR read `'5-26/47'`. Qwen visual encoder corrected it back to `"VMT25-26/147"` using image details.
- **Buyer GSTIN:** OCR read `'GSTNUD33AAA58'`. Qwen dropped it to `""` because it failed structure validation.
- **Item 1 HSN:** OCR read `'9957'`. Qwen read image directly and outputted `"948711"`.
- **Item 4 Desc:** OCR read `'e ch f tn alynma'`. Qwen read visual handwriting and outputted `"turned alarm"`.
- **Line CGST/SGST:** OCR read nothing. Qwen outputted `null` rates due to missing layout columns.
