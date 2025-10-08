"""结构化层缓存 (TODO 1.2 - 3.6)。

提供一个轻量内存 LRU + TTL 缓存:
 - key: 来自 raw_symbols 的稳定 hash (外层应负责计算 / 传入)
 - value: `StructuredPersonaFeatures.to_minimal_dict()` + （可选 full model_dump）
 - TTL: 过期后视为失效并移除
 - 统计: hits / misses / evictions / size / expired_evictions

设计原则:
1. 线程安全简单实现 (GIL 下用 dict + 顺序列表)；后续需要可切换 RLock。
2. 不引入额外依赖；对象序列化使用 pydantic 内置 .model_dump。
3. P1 预留磁盘缓存目录结构（未实现持久化，只是路径占位）。

注意:
 - 该缓存只针对同一进程生命周期；多进程 / 分布式需外部 Redis 等实现。
 - value 默认存最小结构，若需 full 结构可在 set 时传入。
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple

from .schemas import StructuredPersonaFeatures


@dataclass
class CacheEntry:
    key: str
    value: Dict[str, Any]
    created_at: float
    ttl: float

    def is_expired(self, now: Optional[float] = None) -> bool:
        n = now or time.time()
        if self.ttl <= 0:
            return False
        return (n - self.created_at) > self.ttl


@dataclass
class StructuringCacheConfig:
    max_items: int = 256
    default_ttl: float = 3600.0  # 1h
    enable: bool = True
    store_full: bool = False  # 若 True 存放完整 model_dump
    disk_dir: Optional[str] = None  # 预留（未实现持久化）


class StructuringCache:
    def __init__(self, config: Optional[StructuringCacheConfig] = None) -> None:
        self.config = config or StructuringCacheConfig()
        self._data: Dict[str, CacheEntry] = {}
        # LRU 顺序: list 末尾为最近使用；查找 O(1) + 更新 O(n) 对 256 量级可接受
        self._order: list[str] = []
        self._metrics: Dict[str, Any] = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "expired_evictions": 0,
            "sets": 0,
        }
        if self.config.disk_dir:
            os.makedirs(self.config.disk_dir, exist_ok=True)

    # ---------- Internal helpers ---------- #
    def _touch(self, key: str) -> None:
        if key in self._order:
            self._order.remove(key)
        self._order.append(key)

    def _evict_if_needed(self) -> None:
        while len(self._data) > self.config.max_items:
            # FIFO of order's head (least recent)
            oldest = self._order.pop(0)
            self._data.pop(oldest, None)
            self._metrics["evictions"] += 1

    def _reap_expired(self) -> None:
        now = time.time()
        expired_keys = [k for k, e in self._data.items() if e.is_expired(now)]
        if expired_keys:
            for k in expired_keys:
                self._data.pop(k, None)
                if k in self._order:
                    self._order.remove(k)
            self._metrics["expired_evictions"] += len(expired_keys)

    # ---------- Public API ---------- #
    def get(self, key: str) -> Optional[Dict[str, Any]]:
        if not self.config.enable:
            return None
        self._reap_expired()
        entry = self._data.get(key)
        if not entry:
            self._metrics["misses"] += 1
            return None
        if entry.is_expired():
            # 延迟过期
            self._metrics["misses"] += 1
            self._metrics["expired_evictions"] += 1
            self._data.pop(key, None)
            if key in self._order:
                self._order.remove(key)
            return None
        self._metrics["hits"] += 1
        self._touch(key)
        return entry.value

    def set(self, key: str, persona: StructuredPersonaFeatures, ttl: Optional[float] = None) -> None:
        if not self.config.enable:
            return
        ttl_final = ttl if ttl is not None else self.config.default_ttl
        value = persona.model_dump() if self.config.store_full else persona.to_minimal_dict()
        entry = CacheEntry(key=key, value=value, created_at=time.time(), ttl=ttl_final)
        self._data[key] = entry
        self._touch(key)
        self._metrics["sets"] += 1
        self._evict_if_needed()

    def stats(self) -> Dict[str, Any]:
        return {
            **self._metrics,
            "size": len(self._data),
            "order_len": len(self._order),
            "max_items": self.config.max_items,
            "ttl_default": self.config.default_ttl,
            "enabled": self.config.enable,
        }

    def clear(self) -> None:
        self._data.clear()
        self._order.clear()


_GLOBAL_CACHE: Optional[StructuringCache] = None


def get_cache() -> StructuringCache:
    global _GLOBAL_CACHE
    if _GLOBAL_CACHE is None:
        # 允许通过环境变量禁用或调整最大容量
        enable = os.environ.get("BERSONA_STRUCT_CACHE_DISABLE", "0") != "1"
        max_items = int(os.environ.get("BERSONA_STRUCT_CACHE_MAX", "256"))
        ttl = float(os.environ.get("BERSONA_STRUCT_CACHE_TTL", "3600"))
        config = StructuringCacheConfig(max_items=max_items, default_ttl=ttl, enable=enable)
        _GLOBAL_CACHE = StructuringCache(config)
    return _GLOBAL_CACHE


def cache_get(key: str) -> Optional[Dict[str, Any]]:
    return get_cache().get(key)


def cache_set(key: str, persona: StructuredPersonaFeatures, ttl: Optional[float] = None) -> None:
    get_cache().set(key, persona, ttl=ttl)


def cache_stats() -> Dict[str, Any]:
    return get_cache().stats()


__all__ = [
    "StructuringCacheConfig",
    "StructuringCache",
    "cache_get",
    "cache_set",
    "cache_stats",
    "get_cache",
]
