# Redis Forensic Report — Sprint 3
Generated: 2026-07-10 06:17:55 UTC

## 1. Redis Instance Health
| Metric | Pre-Batch Baseline | Post-Batch |
|---|---|---|
| Memory used | 1.2 MB | OK |
| Total key count | 10 | (live) |
| Lock key count | 4 | — |
| Session key count | 1 | — |
| Connected clients | 26 | — |

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
| Finalize lock acquisitions | 17 |
| Finalize lock rejections (contention) | 0 |
| Fair-share throttle events | 8820 |
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
| zcard | 55912 | 2.03 |
| zremrangebyscore | 37345 | 3.44 |
| zrangebyscore | 18734 | 9.5 |
| evalsha | 16507 | 44.56 |
| expire | 8077 | 4.57 |
| hset | 7933 | 6.24 |
| hget | 7381 | 3.68 |
| client | 2794 | 2.84 |
| hgetall | 2350 | 9.89 |
| zrem | 2004 | 7.26 |

## 7. Barrier Bottleneck Events
*No barrier timeouts detected.*

## 8. Verdict
> ✅ **Redis is healthy.** Zero errors and zero disconnection events.