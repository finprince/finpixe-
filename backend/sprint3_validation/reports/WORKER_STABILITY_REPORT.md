# Worker Stability Report — Sprint 3
Generated: 2026-07-02 08:02:01 UTC
Session ID: `820189ef-6b9a-42b2-bbe5-a93408281973`

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
| Files uploaded (UPLOAD_ACCEPTED) | 60 |
| Records created in DB | 62 |
| Queue push successes | 906 |
| Downstream enqueue success | 63 |
| Downstream enqueue failures | 0 |
| DLQ events | 0 |
| Zombie messages | 0 |
| Worker lock refreshes | 613 |

## 3. Success Rates
| Stage | Success Rate |
|---|---|
| Upload → Ingestion queue | 105.0% |
| Ingestion → AI queue | See ingestion.log |
| DLQ contamination rate | 0.0% |

## 4. Worker Crash Events
*No worker crash events detected.*

## 5. DLQ Events
*No DLQ events detected.*

## 6. Verdict
> Worker crashes: **0** | DLQ events: **0** | Zombie messages: **0**
> ✅ **Worker fleet is STABLE. No crashes or DLQ events.**