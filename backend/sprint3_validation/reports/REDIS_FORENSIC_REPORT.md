# Redis Forensic Report — Sprint 3
Generated: 2026-07-02 08:02:01 UTC

## 1. Redis Instance Health
| Metric | Pre-Batch Baseline | Post-Batch |
|---|---|---|
| Memory used | 0.79 MB | OK |
| Total key count | 28 | (live) |
| Lock key count | 0 | — |
| Session key count | 7 | — |
| Connected clients | 7 | — |

## 2. Barrier Latency
| Statistic | Value (ms) |
|---|---|
| Count | 0 |
| Average | 0 ms |
| p50 (Median) | 0 ms |
| p95 | 0 ms |
| p99 | 0 ms |
| Maximum | 0 ms |

## 3. Lock Contention & Orchestration
| Metric | Count |
|---|---|
| Finalize lock acquisitions | 1 |
| Finalize lock rejections (contention) | 0 |
| Fair-share throttle events | 0 |
| Barrier timeouts | 0 |
| Barrier corruption events | 0 |
| Backward state transitions blocked | 0 |
| Lifecycle rejections | 1 |
| Window leaks (watchdog cleanup) | 2 |

## 4. Connection Health
| Metric | Count |
|---|---|
| Redis operation errors | 0 |
| Disconnection events | 0 |
| Reconnection events | 0 |
| Orphaned tasks rescued | 0 |

## 5. Slow Commands
| ID | Duration (μs) | Command |
|---|---|---|
| 2 | 139855 | `b'HSET worker_polling_activity AI_local 1782979242.373718'` |
| 1 | 10959 | `b'HSET worker_polling_activity EXPORT_local 1782973024.82149` |
| 0 | 24414 | `b'EVAL \n        local global_key = KEYS[1]\n        local t` |

## 6. Top Commands by Call Count
| Command | Calls | μs/call |
|---|---|---|
| expire | 4789 | 13.71 |
| hset | 4469 | 42.92 |
| client | 3142 | 4.51 |
| zrem | 1215 | 4.35 |
| zremrangebyscore | 1116 | 5.65 |
| zcard | 772 | 1.04 |
| eval | 425 | 213.96 |
| set | 251 | 22.5 |
| sadd | 226 | 10.27 |
| zadd | 176 | 24.44 |

## 7. Barrier Bottleneck Events
*No barrier timeouts detected.*

## 8. Verdict
> ✅ **Redis is healthy.** Zero errors and zero disconnection events.