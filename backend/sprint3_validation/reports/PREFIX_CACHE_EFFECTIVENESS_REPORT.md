# Prefix Cache Effectiveness Report — Sprint 3
Generated: 2026-07-02 08:02:01 UTC

## Background
The prefix cache works by sharing a common prompt prefix across all pages of the same invoice.
If implemented correctly, all pages of a single invoice should share an identical `PREFIX_HASH`.

**Expected behaviour:**
```
Page 1 → PREFIX_HASH=A
Page 2 → PREFIX_HASH=A
Page 3 → PREFIX_HASH=A
```

## 1. Cache Event Summary
| Metric | Value |
|---|---|
| Total PREFIX_CACHE_TELEMETRY events | 45 |
| Invoices with cache telemetry | 12 |
| Cache-consistent invoices | 8 |
| Cache-invalidated invoices | 1 |
| Single-page invoices (undetermined) | 3 |
| Global unique prefix hashes | 2 |
| Identical prefix ratio | **97.8%** |

## 2. Cache Effectiveness Assessment
> ✅ **Cache is functioning correctly.** 97.8% of prompts share identical prefix hashes.

## 3. Cache-Invalidated Invoices
| Invoice ID | Pages | Unique Prefix Hashes | Root Cause |
|---|---|---|---|
| 1008123 | 2 | 2 | Prompt content differs between pages |

## 4. Verdict
> Sprint 3 prefix cache: **WORKING**
> Consistent invoices: 8 / 9