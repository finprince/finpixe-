# Redis Forensic Report — Sprint 3
Generated: 2026-07-10 05:42:15 UTC

## 1. Redis Instance Health
| Metric | Pre-Batch Baseline | Post-Batch |
|---|---|---|
| Memory used | 0.9 MB | OK |
| Total key count | 14 | (live) |
| Lock key count | 0 | — |
| Session key count | 0 | — |
| Connected clients | 13 | — |

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
| Finalize lock acquisitions | 16 |
| Finalize lock rejections (contention) | 0 |
| Fair-share throttle events | 8631 |
| Barrier timeouts | 0 |
| Barrier corruption events | 0 |
| Backward state transitions blocked | 0 |
| Lifecycle rejections | 20 |
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
| zcard | 27969 | 1.99 |
| zremrangebyscore | 18749 | 3.48 |
| zrangebyscore | 9338 | 9.79 |
| evalsha | 8518 | 45.09 |
| hget | 3336 | 3.78 |
| hset | 3266 | 5.93 |
| expire | 3092 | 4.68 |
| client | 1132 | 2.96 |
| zadd | 1033 | 5.87 |
| zrem | 1006 | 7.28 |

## 7. Barrier Bottleneck Events
*No barrier timeouts detected.*

## 8. Verdict
> ✅ **Redis is healthy.** Zero errors and zero disconnection events.