# Redis Forensic Report — Sprint 3
Generated: 2026-07-08 10:08:55 UTC

## 1. Redis Instance Health
| Metric | Pre-Batch Baseline | Post-Batch |
|---|---|---|
| Memory used | 0.92 MB | OK |
| Total key count | 14 | (live) |
| Lock key count | 0 | — |
| Session key count | 0 | — |
| Connected clients | 14 | — |

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
| Finalize lock acquisitions | 15 |
| Finalize lock rejections (contention) | 0 |
| Fair-share throttle events | 184 |
| Barrier timeouts | 0 |
| Barrier corruption events | 0 |
| Backward state transitions blocked | 0 |
| Lifecycle rejections | 19 |
| Window leaks (watchdog cleanup) | 0 |

## 4. Connection Health
| Metric | Count |
|---|---|
| Redis operation errors | 0 |
| Disconnection events | 0 |
| Reconnection events | 0 |
| Orphaned tasks rescued | 0 |

## 5. Slow Commands
*No slow commands recorded in Redis slow log.*

## 6. Top Commands by Call Count
| Command | Calls | μs/call |
|---|---|---|
| expire | 9404 | 8.93 |
| hset | 7913 | 7.75 |
| client | 4442 | 3.55 |
| hget | 4058 | 2.65 |
| zcard | 1465 | 1.28 |
| zremrangebyscore | 1083 | 3.16 |
| zrem | 748 | 5.73 |
| zadd | 713 | 5.07 |
| hgetall | 708 | 7.22 |
| set | 620 | 8.32 |

## 7. Barrier Bottleneck Events
*No barrier timeouts detected.*

## 8. Verdict
> ✅ **Redis is healthy.** Zero errors and zero disconnection events.