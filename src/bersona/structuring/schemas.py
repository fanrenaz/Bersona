"""Schemas for LLM 结构化特征 (TODO 1.2 之 3.1: Schema 设计)。

本模块定义第一阶段（Structuring Layer）标准化输出的数据结构。
目标：
1. 约束字段与类型，便于下游稳定消费。
2. 提供语义层面轻度清洗与去重。
3. 预留向后兼容扩展槽位 (advanced)。

设计要点：
- 使用 Pydantic v2 (若未来需要可切换至 TypedDict + 自定义校验)。
- List 字段长度限制：strength_traits <= 8, growth_opportunities <= 6。
- 所有字符串在存储前进行 strip 和标准化（目前仅 trim；后续可扩展全角/空白规范化）。
- `validate_semantics()` 负责：
  * 去除重复（保序）
  * 移除空串
  * 返回语义问题列表（不一定抛错，除非严重）

后续扩展（非 3.1 范围，仅预留）:
- schema 升级策略（通过 SCHEMA_VERSION + 迁移函数）
- to_embedding_features() 映射
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, List, Optional, Dict, Set
import hashlib

from pydantic import BaseModel, Field, field_validator, model_validator

SCHEMA_VERSION = "1.0.0"
MAX_STRENGTHS = 8
MAX_GROWTH_OPPS = 6


def _hash_raw_symbols(raw: Dict[str, Any]) -> str:
	"""Create a stable hash of raw symbol dict for traceability/caching keys.

	We sort keys recursively to achieve deterministic hashing. (Shallow for now.)
	"""
	try:
		# Shallow stable repr; if nested dicts appear frequently we can extend.
		items = sorted(raw.items(), key=lambda kv: kv[0])
		payload = repr(items).encode("utf-8")
		return hashlib.sha256(payload).hexdigest()[:16]
	except Exception:
		return "unknown"


class StructuredPersonaFeatures(BaseModel):
	"""标准化后的画像特征 (Structuring Layer Output)。

	字段说明：
	- core_identity: 人格/自我核心主题（精炼短句）
	- motivation: 主要驱动力 / 内在动机
	- decision_style: 决策偏好（逻辑 / 直觉 / 情感 / 实用 等）
	- social_style: 社交表达与互动方式
	- strength_traits: 优势特质列表（1~8）
	- growth_opportunities: 成长机会 / 潜在盲点列表（0~6）
	- advanced: 高保真附加结构（可包含 ascendant_sign 等，对基础消费者透明）
	- fallback: 是否由降级策略生成（非 LLM 正常路径）
	- incomplete_fields: 如果 LLM 输出缺失或被填默认的字段名称列表
	- raw_source_hash: 原始符号字典的哈希（便于调试 / 追溯）
	- schema_version: Schema 版本（对兼容升级很重要）
	- generated_at: ISO 时间戳（UTC）
	"""

	schema_version: str = Field(default=SCHEMA_VERSION)
	generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

	core_identity: str
	motivation: str
	decision_style: str
	social_style: str

	strength_traits: List[str] = Field(default_factory=list)
	growth_opportunities: List[str] = Field(default_factory=list)

	advanced: Optional[Dict[str, Any]] = None

	fallback: bool = False
	incomplete_fields: List[str] = Field(default_factory=list)
	raw_source_hash: Optional[str] = None

	# ------------------ Validators ------------------ #
	@field_validator(
		"core_identity",
		"motivation",
		"decision_style",
		"social_style",
		mode="before",
	)
	@classmethod
	def _clean_scalar(cls, v: Any) -> Any:
		if v is None:
			return "unknown"
		if isinstance(v, str):
			s = v.strip()
			return s if s else "unknown"
		return str(v)

	@field_validator("strength_traits", "growth_opportunities", mode="before")
	@classmethod
	def _ensure_list(cls, v: Any) -> List[str]:
		if v is None:
			return []
		if isinstance(v, (set, tuple)):
			v = list(v)
		if not isinstance(v, list):
			return [str(v)]
		return [str(x) for x in v]

	@model_validator(mode="after")
	def _post_validate(self) -> "StructuredPersonaFeatures":
		# 统一清洗列表 → 去空、去重、截断
		def dedupe_limit(values: List[str], limit: int) -> List[str]:
			seen: Set[str] = set()
			cleaned: List[str] = []
			for x in values:
				sx = x.strip()
				if not sx:
					continue
				# 规范化简单：大小写保留，后续可添加 unicode 归一
				if sx in seen:
					continue
				seen.add(sx)
				cleaned.append(sx)
				if len(cleaned) >= limit:
					break
			return cleaned

		self.strength_traits = dedupe_limit(self.strength_traits, MAX_STRENGTHS)
		self.growth_opportunities = dedupe_limit(
			self.growth_opportunities, MAX_GROWTH_OPPS
		)

		return self

	# ------------------ Public Helpers ------------------ #
	def validate_semantics(self) -> List[str]:
		"""执行额外语义校验，返回问题列表（不抛错）。

		当前实现：检测是否所有核心 scalar 字段全为 "unknown" 或是否列表为空。
		后续可加入：重复语义模式 / 长度过长 / 违禁词过滤等。
		"""
		issues: List[str] = []
		scalar_fields = [
			("core_identity", self.core_identity),
			("motivation", self.motivation),
			("decision_style", self.decision_style),
			("social_style", self.social_style),
		]
		unknown_all = all(v == "unknown" for _, v in scalar_fields)
		if unknown_all:
			issues.append("all_core_scalars_unknown")
		if not self.strength_traits:
			issues.append("empty_strength_traits")
		if len(self.strength_traits) < 2:
			issues.append("few_strength_traits")
		return issues

	@classmethod
	def create_minimal(
		cls,
		core_identity: str = "unknown",
		motivation: str = "unknown",
		decision_style: str = "unknown",
		social_style: str = "unknown",
		strengths: Optional[List[str]] = None,
		growth: Optional[List[str]] = None,
		raw_symbols: Optional[Dict[str, Any]] = None,
		incomplete_fields: Optional[List[str]] = None,
		fallback: bool = True,
	) -> "StructuredPersonaFeatures":
		"""快速构建一个降级结构。"""
		return cls(
			core_identity=core_identity,
			motivation=motivation,
			decision_style=decision_style,
			social_style=social_style,
			strength_traits=strengths or [],
			growth_opportunities=growth or [],
			fallback=fallback,
			incomplete_fields=incomplete_fields or [],
			raw_source_hash=_hash_raw_symbols(raw_symbols or {}),
		)

	def to_minimal_dict(self) -> Dict[str, Any]:
		"""导出一个较小的 dict（可用于缓存 key 或日志）。"""
		return {
			"core_identity": self.core_identity,
			"motivation": self.motivation,
			"decision_style": self.decision_style,
			"social_style": self.social_style,
			"strength_traits": self.strength_traits,
			"growth_opportunities": self.growth_opportunities,
			"fallback": self.fallback,
			"schema_version": self.schema_version,
		}

	# 预留：后续 embedding 特征投影
	def to_embedding_text(self) -> str:  # pragma: no cover (P1 进一步测试)
		return " \n".join(
			[
				self.core_identity,
				self.motivation,
				self.decision_style,
				self.social_style,
				", ".join(self.strength_traits),
				", ".join(self.growth_opportunities),
			]
		)


__all__ = [
	"StructuredPersonaFeatures",
	"SCHEMA_VERSION",
	"MAX_STRENGTHS",
	"MAX_GROWTH_OPPS",
]

