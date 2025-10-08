"""结构化层 Metrics (3.7)。

该模块聚合：
 - 流水线调用次数 / 成功 / fallback
 - 平均耗时 / p95 预估（简化）
 - 缓存命中统计（来自 cache_stats + delta）
 - LLM 调用详细统计（来自 llm.clients.capture_stats）

保持轻量：无需外部依赖，使用简单聚合结构，调用 `snapshot()` 获取当前视图。
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ..llm.clients import collect_llm_metrics
from .cache import cache_stats


@dataclass
class PipelineCounters:
    calls: int = 0
    success: int = 0
    fallback: int = 0
    parse_fail: int = 0
    total_duration_ms: float = 0.0
    durations: List[float] = field(default_factory=list)

    def record(self, duration_ms: float, success: bool, used_fallback: bool, parse_fail: bool):
        self.calls += 1
        if success:
            self.success += 1
        if used_fallback:
            self.fallback += 1
        if parse_fail:
            self.parse_fail += 1
        self.total_duration_ms += duration_ms
        self.durations.append(duration_ms)

    def as_dict(self) -> Dict[str, Any]:
        durations_sorted = sorted(self.durations)
        p95 = None
        if durations_sorted:
            idx = int(len(durations_sorted) * 0.95) - 1
            p95 = durations_sorted[max(0, min(idx, len(durations_sorted) - 1))]
        avg = self.total_duration_ms / self.calls if self.calls else 0.0
        return {
            "calls": self.calls,
            "success": self.success,
            "fallback": self.fallback,
            "parse_fail": self.parse_fail,
            "avg_ms": round(avg, 2),
            "p95_ms": round(p95, 2) if p95 is not None else None,
        }


_PIPELINE_COUNTERS = PipelineCounters()


def record_pipeline(duration_ms: float, success: bool, used_fallback: bool, parse_fail: bool):
    _PIPELINE_COUNTERS.record(duration_ms, success, used_fallback, parse_fail)


def snapshot() -> Dict[str, Any]:
    return {
        "pipeline": _PIPELINE_COUNTERS.as_dict(),
        "cache": cache_stats(),
        "llm": collect_llm_metrics(),
        "timestamp": time.time(),
    }


__all__ = ["record_pipeline", "snapshot"]
