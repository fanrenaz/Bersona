"""LLM 结构化输出解析与校验 (TODO 1.2 - 3.4)。

职责：
1. 从原始模型文本输出中提取第一个 JSON 对象。
2. 解析为字典，补全缺失字段（unknown / []），并记录 incomplete_fields。
3. 基础语义清洗（strip / 去除异常控制字符 / 全角空格 → 半角）。
4. 兼容多余前后缀（模型幻觉加入解释性文字）。
5. 返回 (clean_dict, meta) 供上层构造 `StructuredPersonaFeatures`。

错误处理策略：
- 直接 json.loads 成功 → 使用其结果。
- 失败 → 正则搜索第一个 '{...}' 块（允许跨行，贪婪最小匹配）。
- 再失败 → 抛出 ParseError（上层应进入 fallback）。
"""

from __future__ import annotations

import json
import logging
import re
import unicodedata
from typing import Any, Dict, List, Tuple

from .schemas import (
    StructuredPersonaFeatures,
    MAX_STRENGTHS,
    MAX_GROWTH_OPPS,
)

logger = logging.getLogger("bersona.structuring")

RE_JSON_BLOCK = re.compile(r"\{.*?\}", re.DOTALL)

RE_CONTROL = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F]")

CORE_SCALAR_FIELDS = [
    "core_identity",
    "motivation",
    "decision_style",
    "social_style",
]
LIST_FIELDS = ["strength_traits", "growth_opportunities"]


class ParseError(ValueError):
    pass


def _normalize_str(s: str) -> str:
    # 去除控制字符 + 标准化空格
    s2 = RE_CONTROL.sub("", s)
    # 全角空格 -> 普通空格；再 strip
    s2 = s2.replace("\u3000", " ")
    # NFC 归一
    s2 = unicodedata.normalize("NFC", s2)
    return s2.strip()


def _coerce_to_list(v: Any) -> List[str]:
    if v is None:
        return []
    if isinstance(v, list):
        return [str(x) for x in v]
    if isinstance(v, (set, tuple)):
        return [str(x) for x in v]
    return [str(v)]


def _truncate_list(name: str, values: List[str]) -> List[str]:
    limit = MAX_STRENGTHS if name == "strength_traits" else MAX_GROWTH_OPPS
    cleaned = []
    seen = set()
    for v in values:
        vv = _normalize_str(v)
        if not vv or vv in seen:
            continue
        cleaned.append(vv)
        seen.add(vv)
        if len(cleaned) >= limit:
            break
    return cleaned


def extract_first_json_block(text: str) -> str:
    """尝试从文本中提取第一个 JSON 对象字符串。"""
    # 快路径：直接 loads 成功
    try:
        json.loads(text)
        return text
    except Exception:  # noqa: BLE001
        pass
    # 正则匹配
    match = RE_JSON_BLOCK.search(text)
    if not match:
        raise ParseError("未找到 JSON 块")
    return match.group(0)


def parse_structured_output(raw_text: str) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """解析并校验 LLM 返回文本。

    返回: (data_dict, meta)
      - data_dict: 清洗/补全后的主数据
      - meta: {"incomplete_fields": [...], "raw_length": int, "extracted": bool}
    失败抛出 ParseError。
    """
    if not raw_text or not raw_text.strip():
        raise ParseError("空响应")
    raw_len = len(raw_text)
    extracted = False
    json_block = raw_text
    try:
        json_block = extract_first_json_block(raw_text)
        extracted = json_block != raw_text
        data = json.loads(json_block)
    except ParseError:
        raise
    except Exception as e:  # noqa: BLE001
        raise ParseError(f"JSON 解析失败: {e}") from e

    if not isinstance(data, dict):
        raise ParseError("顶层 JSON 必须是对象")

    incomplete: List[str] = []
    cleaned: Dict[str, Any] = {}

    # 标量字段
    for field in CORE_SCALAR_FIELDS:
        val = data.get(field)
        if not isinstance(val, str):
            val = "unknown"
            incomplete.append(field)
        else:
            val = _normalize_str(val)
            if not val:
                val = "unknown"
                incomplete.append(field)
        cleaned[field] = val

    # 列表字段
    for field in LIST_FIELDS:
        lst = _coerce_to_list(data.get(field))
        tlst = _truncate_list(field, lst)
        if not tlst:
            incomplete.append(field)
        cleaned[field] = tlst

    # advanced 字段（可选）
    advanced = data.get("advanced")
    if isinstance(advanced, dict):
        cleaned["advanced"] = advanced
    else:
        cleaned["advanced"] = {}

    return cleaned, {
        "incomplete_fields": incomplete,
        "raw_length": raw_len,
        "extracted": extracted,
    }


def build_structured_persona(cleaned: Dict[str, Any], meta: Dict[str, Any]) -> StructuredPersonaFeatures:
    """基于解析结果构造 Schema 对象。"""
    return StructuredPersonaFeatures(
        core_identity=cleaned["core_identity"],
        motivation=cleaned["motivation"],
        decision_style=cleaned["decision_style"],
        social_style=cleaned["social_style"],
        strength_traits=cleaned["strength_traits"],
        growth_opportunities=cleaned["growth_opportunities"],
        advanced=cleaned.get("advanced"),
        incomplete_fields=meta.get("incomplete_fields", []),
    )


__all__ = [
    "parse_structured_output",
    "extract_first_json_block",
    "build_structured_persona",
    "ParseError",
]
