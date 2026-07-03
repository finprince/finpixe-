# Failed Invoice RCA Report — Sprint 3
Generated: 2026-07-02 08:02:01 UTC
Session ID: `820189ef-6b9a-42b2-bbe5-a93408281973`

> **Amendment 4**: Validation ran to completion across all 22 invoices.
> All failures collected here — pipeline was NOT stopped on first failure.

## 1. Failure Summary
| Category | Count |
|---|---|
| Timeout | 23 |
| **Total** | **23** |

## 2. Failure Detail by Category

### Timeout

- **IMG_20260319_0001.pdf**: Pipeline timed out after 10 minutes
- **IMG_20260319_0002.pdf**: Pipeline timed out after 10 minutes
- **IMG_20260319_0003.pdf**: Pipeline timed out after 10 minutes
- **IMG_20260319_0004.pdf**: Pipeline timed out after 10 minutes
- **IMG_20260319_0005.pdf**: Pipeline timed out after 10 minutes
- **IMG_20260319_0006.pdf**: Pipeline timed out after 10 minutes
- **IMG_20260319_0007.pdf**: Pipeline timed out after 10 minutes
- **IMG_20260319_0008.pdf**: Pipeline timed out after 10 minutes
- **IMG_20260319_0009.pdf**: Pipeline timed out after 10 minutes
- **IMG_20260319_0010.pdf**: Pipeline timed out after 10 minutes

## 3. Log Evidence
Refer to `WORKER_STABILITY_RAW.json` and `REDIS_FORENSICS_RAW.json` for raw log lines.

## 4. Proposed Fixes
| Category | Proposed Fix |
|---|---|
| Upload Failure | Increase API timeout, check multipart size limits |
| OCR Failure | Verify PaddleOCR subprocess memory limit |
| AI/Qwen Failure | Check Ollama GPU availability, increase retry count |
| Timeout | Increase SESSION_POLL_TIMEOUT_S, check queue backlog |
| Assembly Failure | Verify barrier convergence logic |

## 5. Verdict
> Total failures: **23** out of 22 invoices.
> ❌ **Significant failures — requires remediation before production.**