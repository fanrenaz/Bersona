import json
import os
import time

import pytest

from bersona.structuring.schemas import StructuredPersonaFeatures
from bersona.structuring.parser import parse_structured_output, build_structured_persona, ParseError
from bersona.structuring.fallback import build_fallback_persona
from bersona.structuring.cache import cache_get, cache_set, cache_stats, get_cache, StructuringCacheConfig, StructuringCache
from bersona.structuring.engine import structure_features
from bersona.structuring.metrics import snapshot
from bersona.structuring.engine import structure_features_batch


def test_schema_minimal_creation():
    obj = StructuredPersonaFeatures.create_minimal(
        core_identity="分析", motivation="成长", decision_style="逻辑", social_style="克制", strengths=["专注", "精确"], growth=["放松"], raw_symbols={}
    )
    assert obj.core_identity == "分析"
    assert len(obj.strength_traits) == 2
    assert obj.schema_version == "1.0.0"


def test_parse_success_and_incomplete():
    raw = '{"core_identity":"A","motivation":"","decision_style":123,"social_style":"  ","strength_traits":[],"growth_opportunities":null}'
    cleaned, meta = parse_structured_output("前缀\n" + raw)
    assert cleaned["core_identity"] == "A"
    assert len(meta["incomplete_fields"]) >= 3
    persona = build_structured_persona(cleaned, meta)
    assert isinstance(persona, StructuredPersonaFeatures)


def test_parse_error_triggers_exception():
    with pytest.raises(ParseError):
        parse_structured_output("not a json at all")


def test_fallback_from_sun_sign():
    fb = build_fallback_persona({"astrology_raw": {"sun_sign": "Virgo"}})
    assert fb.fallback is True
    assert fb.core_identity != "unknown"


def test_cache_get_set():
    cache = get_cache()
    cache.clear()
    persona = StructuredPersonaFeatures.create_minimal(core_identity="X", motivation="Y", decision_style="Z", social_style="S", strengths=["A","B"], growth=["G"], raw_symbols={})
    cache_set("demo", persona, ttl=1)
    assert cache_get("demo") is not None
    stats1 = cache_stats()
    assert stats1["hits"] == 1  # get 会 +1 hits
    time.sleep(1.05)
    _ = cache_get("demo")  # 过期
    stats2 = cache_stats()
    assert stats2["expired_evictions"] >= 1


def test_pipeline_structure_and_cache_hit(monkeypatch):
    # mock generate_json 返回固定 JSON
    from bersona.llm import clients

    def fake_generate(prompt, **kw):  # noqa: D401
        return '{"core_identity":"精简","motivation":"提升","decision_style":"逻辑","social_style":"稳健","strength_traits":["分析","执行"],"growth_opportunities":["放松"],"advanced":{}}'

    monkeypatch.setattr(clients, "generate_json", fake_generate)

    raw = {"astrology_raw": {"sun_sign": "Virgo"}}
    # 清缓存确保第一次 miss
    get_cache().clear()
    p1 = structure_features(raw, model="stub-1")
    assert p1.fallback is False
    p2 = structure_features(raw, model="stub-1")
    assert p2.core_identity == p1.core_identity
    # 第二次应命中缓存（metrics 可侧面验证 hits 增长）
    snap = snapshot()
    assert snap["cache"]["hits"] >= 1


def test_pipeline_fallback_on_parse_fail(monkeypatch):
    from bersona.llm import clients

    def bad_generate(prompt, **kw):
        return "完全坏掉的输出 !!!"  # 解析失败触发 fallback

    monkeypatch.setattr(clients, "generate_json", bad_generate)
    raw = {"astrology_raw": {"sun_sign": "Aries"}}
    get_cache().clear()
    persona = structure_features(raw)
    assert persona.fallback is True
    assert persona.core_identity != "unknown"


def test_metrics_snapshot_shape():
    snap = snapshot()
    assert "pipeline" in snap and "cache" in snap and "llm" in snap
    assert isinstance(snap["pipeline"].get("calls"), int)


def test_redact_inputs_logging(monkeypatch, caplog):
    from bersona.llm import clients

    def fake_generate(prompt, **kw):
        return '{"core_identity": "A", "motivation": "B", "decision_style": "C", "social_style": "D", "strength_traits": ["X"], "growth_opportunities": ["Y"], "advanced": {}}'

    monkeypatch.setattr(clients, "generate_json", fake_generate)
    raw = {"astrology_raw": {"sun_sign": "Virgo", "moon_sign": "Capricorn"}}
    caplog.set_level("INFO")
    _ = structure_features(raw, model="stub-1", redact_inputs=True, use_cache=False)
    redacted_lines = [r.message for r in caplog.records if "structure_features done" in r.message]
    assert any("['moon_sign', 'sun_sign']" in line for line in redacted_lines)
    assert all("Virgo" not in line for line in redacted_lines)  # 确认未出现原始值

    caplog.clear()
    _ = structure_features(raw, model="stub-1", redact_inputs=False, use_cache=False)
    full_lines = [r.message for r in caplog.records if "structure_features done" in r.message]
    assert any("Virgo" in line for line in full_lines)


def test_batch_basic_and_dedupe(monkeypatch):
    from bersona.llm import clients

    calls = {"n": 0}

    def fake_generate(prompt, **kw):
        calls["n"] += 1
        # 返回批量数组：两个 Virgo（用同一结果）+ 一个 Aries
        return '[{"core_identity": "A", "motivation": "B", "decision_style": "C", "social_style": "D", "strength_traits": ["X"], "growth_opportunities": ["Y"], "advanced": {}}, {"core_identity": "A2", "motivation": "B2", "decision_style": "C2", "social_style": "D2", "strength_traits": ["X2"], "growth_opportunities": ["Y2"], "advanced": {}}]'

    monkeypatch.setattr(clients, "generate_json", fake_generate)

    raws = [
        {"astrology_raw": {"sun_sign": "Virgo"}},
        {"astrology_raw": {"sun_sign": "Virgo"}},  # duplicate
        {"astrology_raw": {"sun_sign": "Aries"}},
    ]
    res = structure_features_batch(raws, model="stub-1", parallel=False, dedupe=True)
    assert len(res) == 3
    # 合并批量：仅一次调用
    assert calls["n"] == 1
    assert [r.core_identity for r in res[:2]].count("A") >= 1
    assert any(r.core_identity in {"A2"} for r in res)


def test_batch_parallel(monkeypatch):
    from bersona.llm import clients

    def fake_generate(prompt, **kw):
        return '{"core_identity": "P", "motivation": "Q", "decision_style": "R", "social_style": "S", "strength_traits": ["T"], "growth_opportunities": ["U"], "advanced": {}}'

    monkeypatch.setattr(clients, "generate_json", fake_generate)
    raws = [{"astrology_raw": {"sun_sign": f"Sign{i}"}} for i in range(4)]
    res = structure_features_batch(raws, model="stub-1", parallel=True)
    assert len(res) == 4
    assert {r.core_identity for r in res} == {"P"}


def test_batch_merged_single_call(monkeypatch):
    from bersona.llm import clients

    calls = {"n": 0}

    def fake_generate(prompt, **kw):
        calls["n"] += 1
        # 返回两个对象数组 JSON
        return '[{"core_identity": "X1", "motivation": "M1", "decision_style": "D1", "social_style": "S1", "strength_traits": ["A"], "growth_opportunities": ["B"], "advanced": {}}, {"core_identity": "X2", "motivation": "M2", "decision_style": "D2", "social_style": "S2", "strength_traits": ["C"], "growth_opportunities": ["D"], "advanced": {}}]'

    monkeypatch.setattr(clients, "generate_json", fake_generate)
    raws = [
        {"astrology_raw": {"sun_sign": "Virgo"}},
        {"astrology_raw": {"sun_sign": "Aries"}},
    ]
    res = structure_features_batch(raws, parallel=False, dedupe=True)
    assert calls["n"] == 1  # 合并路径只调用一次
    assert [r.core_identity for r in res] == ["X1", "X2"]
