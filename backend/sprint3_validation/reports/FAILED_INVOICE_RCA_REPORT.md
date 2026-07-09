# Failed Invoice RCA Report — Sprint 3
Generated: 2026-07-09 11:47:17 UTC
Session ID: `0880bd29-3f55-4858-a495-2960ba29bb89`

> **Amendment 4**: Validation ran to completion across all 22 invoices.
> All failures collected here — pipeline was NOT stopped on first failure.

## 1. Failure Summary
| Category | Count |
|---|---|
| Unknown | 1 |
| **Total** | **1** |

## 2. Failure Detail by Category

### Unknown

- **IMG_20260406_0006_TEST.pdf**: Pipeline status: FAILED

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
> Total failures: **1** out of 22 invoices.
> ⚠️ **Minor failure rate — investigate specific invoices.**