# Worker Stability Report — Sprint 3
Generated: 2026-07-10 05:42:15 UTC
Session ID: `52a295f6-c9be-48fd-9178-f36e7422713d`

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
| Queue push successes | 312 |
| Downstream enqueue success | 37 |
| Downstream enqueue failures | 0 |
| DLQ events | 0 |
| Zombie messages | 0 |
| Worker lock refreshes | 203 |

## 3. Success Rates
| Stage | Success Rate |
|---|---|
| Upload → Ingestion queue | 160.9% |
| Ingestion → AI queue | See ingestion.log |
| DLQ contamination rate | 0.0% |

## 4. Worker Crash Events
*No worker crash events detected.*

## 5. DLQ Events
*No DLQ events detected.*

## 6. Verdict
> Worker crashes: **0** | DLQ events: **0** | Zombie messages: **0**
> ✅ **Worker fleet is STABLE. No crashes or DLQ events.**