# Worker Stability Report — Sprint 3
Generated: 2026-07-09 11:47:17 UTC
Session ID: `0880bd29-3f55-4858-a495-2960ba29bb89`

## 1. Worker Fleet Status
| Worker Role | Starts Detected | Crashes | Status |
|---|---|---|---|
| ingestion | 0 | 0 | ✅ STABLE |
| ai | 0 | 0 | ✅ STABLE |
| assembly | 0 | 0 | ✅ STABLE |
| finalize | 0 | 0 | ✅ STABLE |
| export | 0 | 0 | ✅ STABLE |
| materialization | 0 | 0 | ✅ STABLE |

## 2. Pipeline Throughput
| Metric | Count |
|---|---|
| Files uploaded (UPLOAD_ACCEPTED) | 23 |
| Records created in DB | 23 |
| Queue push successes | 324 |
| Downstream enqueue success | 42 |
| Downstream enqueue failures | 0 |
| DLQ events | 0 |
| Zombie messages | 0 |
| Worker lock refreshes | 369 |

## 3. Success Rates
| Stage | Success Rate |
|---|---|
| Upload → Ingestion queue | 182.6% |
| Ingestion → AI queue | See ingestion.log |
| DLQ contamination rate | 0.0% |

## 4. Worker Crash Events
*No worker crash events detected.*

## 5. DLQ Events
*No DLQ events detected.*

## 6. Verdict
> Worker crashes: **0** | DLQ events: **0** | Zombie messages: **0**
> ✅ **Worker fleet is STABLE. No crashes or DLQ events.**