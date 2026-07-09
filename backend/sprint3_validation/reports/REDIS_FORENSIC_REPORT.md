# Redis Forensic Report — Sprint 3
Generated: 2026-07-09 11:47:17 UTC

## 1. Redis Instance Health
| Metric | Pre-Batch Baseline | Post-Batch |
|---|---|---|
| Memory used | 0.78 MB | OK |
| Total key count | 13 | (live) |
| Lock key count | 0 | — |
| Session key count | 0 | — |
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
| Finalize lock acquisitions | 23 |
| Finalize lock rejections (contention) | 0 |
| Fair-share throttle events | 9247 |
| Barrier timeouts | 0 |
| Barrier corruption events | 0 |
| Backward state transitions blocked | 0 |
| Lifecycle rejections | 22 |
| Window leaks (watchdog cleanup) | 0 |

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
| 0 | 65772 | `b'HSET worker_heartbeats EXPORT_local 1783595091.2099779'` |

## 6. Top Commands by Call Count
| Command | Calls | μs/call |
|---|---|---|
| zcard | 45960 | 1.87 |
| zremrangebyscore | 31393 | 3.39 |
| hget | 29727 | 3.89 |
| expire | 29546 | 6.14 |
| hset | 28856 | 9.15 |
| zrangebyscore | 14550 | 9.74 |
| client | 12250 | 3.38 |
| evalsha | 12065 | 42.95 |
| zrem | 6182 | 7.68 |
| zadd | 5991 | 5.97 |

## 7. Barrier Bottleneck Events
*No barrier timeouts detected.*

## 8. Verdict
> ✅ **Redis is healthy.** Zero errors and zero disconnection events.