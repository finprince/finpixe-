# Redis Forensic Report — Sprint 3
Generated: 2026-07-10 08:15:03 UTC

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
| Finalize lock acquisitions | 15 |
| Finalize lock rejections (contention) | 0 |
| Fair-share throttle events | 3268 |
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
| zcard | 111083 | 1.98 |
| zremrangebyscore | 74164 | 3.36 |
| zrangebyscore | 37324 | 9.26 |
| evalsha | 31802 | 43.27 |
| hget | 26163 | 2.46 |
| expire | 20542 | 4.6 |
| hset | 18960 | 6.04 |
| client | 7154 | 2.66 |
| hgetall | 5072 | 9.57 |
| eval | 4956 | 55.04 |

## 7. Barrier Bottleneck Events
*No barrier timeouts detected.*

## 8. Verdict
> ✅ **Redis is healthy.** Zero errors and zero disconnection events.