# Worker Stability Report — Sprint 3
Generated: 2026-07-10 06:53:08 UTC
Session ID: `196c7dde-7327-445d-8db0-7ae415dd05c1`

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
| Queue push successes | 219 |
| Downstream enqueue success | 32 |
| Downstream enqueue failures | 0 |
| DLQ events | 0 |
| Zombie messages | 0 |
| Worker lock refreshes | 325 |

## 3. Success Rates
| Stage | Success Rate |
|---|---|
| Upload → Ingestion queue | 139.1% |
| Ingestion → AI queue | See ingestion.log |
| DLQ contamination rate | 0.0% |

## 4. Worker Crash Events
*No worker crash events detected.*

## 5. DLQ Events
*No DLQ events detected.*

## 6. Verdict
> Worker crashes: **0** | DLQ events: **0** | Zombie messages: **0**
> ✅ **Worker fleet is STABLE. No crashes or DLQ events.**