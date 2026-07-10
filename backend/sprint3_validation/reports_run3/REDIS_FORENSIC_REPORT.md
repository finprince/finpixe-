# Redis Forensic Report — Sprint 3
Generated: 2026-07-10 06:53:08 UTC

## 1. Redis Instance Health
| Metric | Pre-Batch Baseline | Post-Batch |
|---|---|---|
| Memory used | 1.24 MB | OK |
| Total key count | 11 | (live) |
| Lock key count | 0 | — |
| Session key count | 2 | — |
| Connected clients | 28 | — |

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
| Finalize lock acquisitions | 7 |
| Finalize lock rejections (contention) | 0 |
| Fair-share throttle events | 8819 |
| Barrier timeouts | 0 |
| Barrier corruption events | 0 |
| Backward state transitions blocked | 0 |
| Lifecycle rejections | 17 |
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
| zcard | 83477 | 1.99 |
| zremrangebyscore | 55706 | 3.38 |
| zrangebyscore | 28057 | 9.23 |
| evalsha | 24082 | 43.63 |
| expire | 11878 | 4.48 |
| hset | 11253 | 6.21 |
| hget | 9361 | 3.68 |
| client | 4156 | 2.76 |
| eval | 3569 | 55.91 |
| hgetall | 3082 | 9.82 |

## 7. Barrier Bottleneck Events
*No barrier timeouts detected.*

## 8. Verdict
> ✅ **Redis is healthy.** Zero errors and zero disconnection events.