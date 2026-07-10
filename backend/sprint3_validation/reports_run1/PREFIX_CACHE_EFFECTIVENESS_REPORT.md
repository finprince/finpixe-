# Prefix Cache Effectiveness Report — Sprint 3
Generated: 2026-07-10 05:42:15 UTC

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
| Total PREFIX_CACHE_TELEMETRY events | 0 |
| Invoices with cache telemetry | 0 |
| Cache-consistent invoices | 0 |
| Cache-invalidated invoices | 0 |
| Single-page invoices (undetermined) | 0 |
| Global unique prefix hashes | 0 |
| Identical prefix ratio | **0%** |

## 2. Cache Effectiveness Assessment
> ⚠️ **No PREFIX_CACHE_TELEMETRY events found.** Cache may not be enabled or logs are empty.

## 3. Cache-Invalidated Invoices
*No cache invalidations detected.*

## 4. Verdict
> Sprint 3 prefix cache: **NEEDS INVESTIGATION**
> Consistent invoices: 0 / 0