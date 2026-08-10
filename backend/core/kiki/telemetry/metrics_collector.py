"""
KIKI Telemetry Metrics Collector
================================
Tracks model latencies, token counts, cache hits/misses, and sub-service health metrics.
"""
import time
from typing import Dict, Any

class MetricsCollector:
    def __init__(self):
        self._metrics: Dict[str, Any] = {
            "total_requests": 0,
            "failed_requests": 0,
            "router_latency_ms": [],
            "reasoning_latency_ms": [],
            "query_engine_latency_ms": [],
            "cache_hits": 0,
            "cache_misses": 0
        }

    def record_latency(self, metric_name: str, latency_ms: float) -> None:
        if metric_name in self._metrics and isinstance(self._metrics[metric_name], list):
            self._metrics[metric_name].append(latency_ms)
            # Keep rolling window of last 1000 measurements
            if len(self._metrics[metric_name]) > 1000:
                self._metrics[metric_name].pop(0)

    def increment_counter(self, counter_name: str, amount: int = 1) -> None:
        if counter_name in self._metrics and isinstance(self._metrics[counter_name], int):
            self._metrics[counter_name] += amount

    def get_summary(self) -> Dict[str, Any]:
        def avg(lst):
            return sum(lst) / len(lst) if lst else 0.0

        return {
            "total_requests": self._metrics["total_requests"],
            "failed_requests": self._metrics["failed_requests"],
            "avg_router_latency_ms": round(avg(self._metrics["router_latency_ms"]), 2),
            "avg_reasoning_latency_ms": round(avg(self._metrics["reasoning_latency_ms"]), 2),
            "avg_query_engine_latency_ms": round(avg(self._metrics["query_engine_latency_ms"]), 2),
            "cache_hits": self._metrics["cache_hits"],
            "cache_misses": self._metrics["cache_misses"],
            "cache_hit_ratio": round(
                self._metrics["cache_hits"] / max(1, (self._metrics["cache_hits"] + self._metrics["cache_misses"])), 4
            )
        }

metrics_collector = MetricsCollector()
