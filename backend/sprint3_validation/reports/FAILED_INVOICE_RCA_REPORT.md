# Failed Invoice RCA Report — Sprint 3
Generated: 2026-07-10 08:15:03 UTC
Session ID: `f46bcfc9-28d8-4623-abef-a5ca828181f3`

> **Amendment 4**: Validation ran to completion across all 22 invoices.
> All failures collected here — pipeline was NOT stopped on first failure.

## 1. Failure Summary
| Category | Count |
|---|---|
| Unknown | 5 |
| **Total** | **5** |

## 2. Failure Detail by Category

### Unknown

- **IMG_20260406_0006_TEST.pdf**: Pipeline status: FAILED
- **1008704**: DB record in FAILED state
- **1008706**: DB record in FAILED state
- **1008707**: DB record in FAILED state
- **1008715**: DB record in FAILED state

## 3. Log Evidence
Refer to `WORKER_STABILITY_RAW.json` and `REDIS_FORENSICS_RAW.json` for raw log lines.

## 4. Proposed Fixes
| Category | Proposed Fix |
|---|---|
| Upload Failure | Increase API timeout, check multipart size limits |
| OCR Failure | Verify MISTRAL_API_KEY and Mistral API connectivity |
| AI/Mistral Failure | Check Mistral API key, rate limits, or response quality |
| Timeout | Increase SESSION_POLL_TIMEOUT_S, check queue backlog |
| Assembly Failure | Verify barrier convergence logic |

## 5. Verdict
> Total failures: **5** out of 22 invoices.
> ❌ **Significant failures — requires remediation before production.**