"""结构化层统一入口 (集成缓存/LLM/解析/fallback/metrics & logging) — 对应 TODO 1.2 P0 #1。

使用方式:
    from bersona.structuring.engine import structure_features
    persona = structure_features(raw_symbols)
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any, Dict, Optional

from .schemas import StructuredPersonaFeatures, _hash_raw_symbols
from .fallback import build_fallback_persona
from .parser import parse_structured_output, build_structured_persona, ParseError
from .cache import cache_get, cache_set
from .metrics import record_pipeline
from ..llm.prompts import STRUCTURE_PROMPT_TEMPLATE, BATCH_STRUCTURE_PROMPT_TEMPLATE
from ..llm import clients as llm_clients

logger = logging.getLogger("bersona.structuring")


def _render_prompt(raw_symbols: Dict[str, Any]) -> str:
    return STRUCTURE_PROMPT_TEMPLATE.replace(
        "{raw_symbols_json}", json.dumps(raw_symbols, ensure_ascii=False)
    )


def structure_features(
    raw_symbols: Dict[str, Any],
    *,
    context: Optional[Dict[str, Any]] = None,
    model: str = "stub-1",
    fallback_models: Optional[list[str]] = None,
    use_cache: bool = True,
    max_retries: int = 2,
    temperature: float = 0.3,
    timeout: float | None = 40.0,
    redact_inputs: bool = True,
) -> StructuredPersonaFeatures:
    """主入口：返回结构化画像特征。

    流程：cache -> prompt -> LLM -> parse -> schema | fallback -> cache set -> metrics
    失败路径：LLM 全部失败 或 解析失败 -> fallback persona
    """
    start = time.time()
    cache_key = _hash_raw_symbols(raw_symbols)
    parse_fail = False
    used_fallback = False

    if use_cache:
        cached = cache_get(cache_key)
        if cached:
            persona = StructuredPersonaFeatures.create_minimal(
                core_identity=cached["core_identity"],
                motivation=cached["motivation"],
                decision_style=cached["decision_style"],
                social_style=cached["social_style"],
                strengths=cached.get("strength_traits", []),
                growth=cached.get("growth_opportunities", []),
                raw_symbols=raw_symbols,
                fallback=cached.get("fallback", False),
            )
            record_pipeline((time.time() - start) * 1000, True, persona.fallback, False)
            return persona

    # 组装 Prompt & 调用 LLM
    prompt = _render_prompt(raw_symbols)
    llm_stats: Dict[str, Any] = {}
    try:
        # 运行时查找，便于测试 monkeypatch (避免 import 绑定早期快照)
        llm_text = llm_clients.generate_json(  # type: ignore[attr-defined]
            prompt,
            model=model,
            fallback_models=fallback_models,
            max_retries=max_retries,
            temperature=temperature,
            timeout=timeout,
            raise_on_failure=True,
            capture_stats=llm_stats,
        )
    except Exception as e:  # noqa: BLE001
        logger.error("LLM 调用失败 -> fallback: %s", e)
        persona = build_fallback_persona(raw_symbols)
        used_fallback = True
        if use_cache:
            cache_set(cache_key, persona)
        record_pipeline((time.time() - start) * 1000, True, used_fallback, False)
        return persona

    # 解析
    try:
        cleaned, meta = parse_structured_output(llm_text)
        persona = build_structured_persona(cleaned, meta)
    except ParseError as e:
        logger.warning("解析失败(%s) -> fallback", e)
        parse_fail = True
        persona = build_fallback_persona(raw_symbols)
        used_fallback = True

    if use_cache and not persona.fallback:  # 仅缓存非 fallback 结果（策略可调整）
        cache_set(cache_key, persona)

    duration_ms = (time.time() - start) * 1000
    # 输入日志（遵循隐私：默认仅输出键）
    if redact_inputs:
        input_repr = {k: (sorted(v.keys()) if isinstance(v, dict) else "<val>") for k, v in raw_symbols.items()}
    else:
        input_repr = raw_symbols

    logger.info(
        "structure_features done model=%s fb=%s parse_fail=%s dur=%.2fms key=%s attempts=%s input=%s",
        llm_stats.get("final_model"),
        used_fallback,
        parse_fail,
        duration_ms,
        cache_key,
        llm_stats.get("attempts"),
        input_repr,
    )
    record_pipeline(duration_ms, True, used_fallback, parse_fail)
    return persona


__all__ = ["structure_features"]


def structure_features_batch(
    items: list[Dict[str, Any]],
    *,
    model: str = "stub-1",
    fallback_models: Optional[list[str]] = None,
    use_cache: bool = True,
    max_retries: int = 2,
    temperature: float = 0.3,
    timeout: float | None = 40.0,
    redact_inputs: bool = True,
    parallel: bool = False,
    max_workers: int | None = None,
    dedupe: bool = True,
) -> list[StructuredPersonaFeatures]:
    """批量结构化入口（P2）。

    特性：
    - 复用单条 `structure_features` 逻辑（含缓存 / fallback / metrics）。
    - 可选去重：相同 raw symbols（哈希）只计算一次（若关闭缓存仍有意义）。
    - 可选并行：ThreadPoolExecutor（LLM I/O 场景典型为 I/O bound）。

    约束：
    - 当前实现简单聚合；整体不失败短路，逐条隔离错误（捕获异常 -> 单条 fallback）。
    - metrics 仍由内部逐条调用记录；此函数不额外聚合返回指标。
    """

    if not items:
        return []

    # 去重映射
    order: list[str] = []
    hashed_inputs: dict[str, Dict[str, Any]] = {}
    if dedupe:
        for raw in items:
            h = _hash_raw_symbols(raw)
            order.append(h)
            if h not in hashed_inputs:
                hashed_inputs[h] = raw
    else:
        # 不去重时仍使用唯一 key（索引+hash）避免覆盖。
        for idx, raw in enumerate(items):
            h = f"{idx}:{_hash_raw_symbols(raw)}"
            order.append(h)
            hashed_inputs[h] = raw

    results_map: dict[str, StructuredPersonaFeatures] = {}

    def _process(raw: Dict[str, Any]) -> StructuredPersonaFeatures:
        try:
            return structure_features(
                raw,
                model=model,
                fallback_models=fallback_models,
                use_cache=use_cache,
                max_retries=max_retries,
                temperature=temperature,
                timeout=timeout,
                redact_inputs=redact_inputs,
            )
        except Exception:  # noqa: BLE001
            # 双重保险：如果内部出现未捕获异常，回退到 fallback persona
            return build_fallback_persona(raw)

    # 优先尝试批量合并调用（仅在未显式并行且条目数>1时）
    if not parallel and len(hashed_inputs) > 1:
        try:
            # 构造批量 prompt：保持原始顺序输入（去重后也需映射回原顺序）
            # 使用去重后的 raw 列表；重复项稍后映射。
            batch_raw_list = list(hashed_inputs.values())
            import json as _json

            prompt = BATCH_STRUCTURE_PROMPT_TEMPLATE.replace(
                "{raw_symbols_batch_json}", _json.dumps(batch_raw_list, ensure_ascii=False)
            )
            from ..llm import clients as _llm_clients  # 延迟导入

            llm_stats: Dict[str, Any] = {}
            text = _llm_clients.generate_json(
                prompt,
                model=model,
                fallback_models=fallback_models,
                max_retries=max_retries,
                temperature=temperature,
                timeout=timeout,
                raise_on_failure=True,
                capture_stats=llm_stats,
            )
            # 解析：期望是 JSON 数组
            import json as _j

            arr = None
            try:
                arr = _j.loads(text)
            except Exception:  # noqa: BLE001
                # 尝试截取首个 [] 块
                import re as _re

                m = _re.search(r"\[[\s\S]*\]", text)
                if m:
                    try:
                        arr = _j.loads(m.group(0))
                    except Exception:  # noqa: BLE001
                        arr = None
            if isinstance(arr, list) and len(arr) == len(batch_raw_list):
                # 将每个对象送入 build_structured_persona 流程（复用单条解析补默认逻辑较复杂，这里直接走简化路径：假设模型已给全字段）
                built: list[StructuredPersonaFeatures] = []
                for idx, obj in enumerate(arr):
                    if not isinstance(obj, dict):
                        raise ValueError("batch item not dict")
                    # 补字段缺失
                    for req in [
                        "core_identity",
                        "motivation",
                        "decision_style",
                        "social_style",
                        "strength_traits",
                        "growth_opportunities",
                    ]:
                        obj.setdefault(req, "unknown" if "traits" not in req else [])
                    try:
                        built.append(
                            StructuredPersonaFeatures(
                                **{
                                    k: obj.get(k)
                                    for k in [
                                        "core_identity",
                                        "motivation",
                                        "decision_style",
                                        "social_style",
                                        "strength_traits",
                                        "growth_opportunities",
                                        "advanced",
                                    ]
                                }
                            )
                        )
                    except Exception:
                        built.append(build_fallback_persona(batch_raw_list[idx]))
                # 映射回原顺序（去重：同一 hash 用同一对象）
                map_seq: dict[str, StructuredPersonaFeatures] = {}
                for h_key, raw in hashed_inputs.items():
                    # index via iteration order
                    idx = batch_raw_list.index(raw)
                    map_seq[h_key] = built[idx]
                return [map_seq[h] for h in order]
        except Exception:  # noqa: BLE001
            # 批量路径失败，回退逐条策略
            pass

    if parallel and len(hashed_inputs) > 1:
        from concurrent.futures import ThreadPoolExecutor

        with ThreadPoolExecutor(max_workers=max_workers or min(8, len(hashed_inputs))) as ex:
            future_map = {ex.submit(_process, raw): h for h, raw in hashed_inputs.items()}
            for fut in future_map:
                h = future_map[fut]
                try:
                    results_map[h] = fut.result()
                except Exception:  # pragma: no cover - 理论上 _process 已处理
                    results_map[h] = build_fallback_persona(hashed_inputs[h])
    else:
        for h, raw in hashed_inputs.items():
            results_map[h] = _process(raw)

    # 按顺序重建列表
    return [results_map[h] for h in order]


__all__.append("structure_features_batch")
