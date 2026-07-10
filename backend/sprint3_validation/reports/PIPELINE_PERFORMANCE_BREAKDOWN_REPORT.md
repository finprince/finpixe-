# Pipeline Performance Breakdown Report — Sprint 3
Generated: 2026-07-10 08:15:03 UTC  *(Amendment 2)*
Session ID: `f46bcfc9-28d8-4623-abef-a5ca828181f3`

## 1. Per-Stage Latency Statistics (ms)
| Stage | Events (n) | Avg | Median | p95 | p99 | Max |
|---|---|---|---|---|---|---|
| OCR | N/A | N/A | N/A | N/A | N/A | N/A |
| AI Extraction (Mistral) | 180 | 1287.4 | 915.0 | 2880.0 | 8440.0 | 9960.0 |
| Assembly | N/A | N/A | N/A | N/A | N/A | N/A |
| Finalization | N/A | N/A | N/A | N/A | N/A | N/A |
| **Total Pipeline** | N/A | N/A | N/A | N/A | N/A | N/A |

## 2. Bottleneck Ranking (by Cumulative Processing Time)
| Rank | Stage | Cumulative Time (ms) | % of Total |
|---|---|---|---|
| 1 | AI Extraction (Mistral) | 231,730 | **100.0%** |
| 2 | OCR | 0 | **0.0%** |
| 3 | Assembly | 0 | **0.0%** |
| 4 | Finalization | 0 | **0.0%** |

## 3. Bottleneck Analysis
> **Primary bottleneck: AI Extraction (Mistral)** (100.0% of cumulative pipeline time)
> 
> AI extraction dominates pipeline time. Optimization paths:
> - Increase `WORKER_CONCURRENCY` (currently 4) if GPU headroom allows
> - Validate prefix cache hit ratio (see PREFIX_CACHE_EFFECTIVENESS_REPORT.md)
> - Consider batch-image mode for multi-page invoices

## 4. WORKER_CONCURRENCY=4 Assessment
| Metric | Value |
|---|---|
| Configured concurrency | 4 |
| AI p95 latency | 2880.0 ms |
| Total pipeline p95 | N/A ms |

> If AI p95 latency > 60,000 ms, concurrency of 4 is a throughput bottleneck.
> If AI p95 latency < 30,000 ms, concurrency of 4 is likely appropriate.

## 5. Recommendations
Based on the data above, refer to PRODUCTION_VALIDATION_SIGNOFF.md for the final verdict.