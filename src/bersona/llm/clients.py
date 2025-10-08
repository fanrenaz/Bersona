"""LLM 客户端封装 (3.3 实现)。

功能目标：
1. 提供 `generate_json` 统一入口：接受 prompt，返回文本（期望为 JSON）。
2. 支持重试（指数退避）、fallback 模型链、超时控制（软实现）。
3. 提供统一异常 `LLMClientError`。
4. 记录基础 metrics（累计：调用次数/成功/失败/重试/模型级别耗时）。
5. 可在无外部依赖(openai未安装 / 无 API KEY) 情况下工作（降级到 stub）。

设计简化：
- 不强制引入第三方 SDK；openai 若可用则使用。
- fallback 链：按顺序尝试；如果模型名以 `stub` 开头直接使用 stub 响应。
- tokens 统计：若 SDK 返回则填充，否则为 None。

后续可扩展：
- 更多 Provider（Anthropic / 自托管 Llama）
- 流式输出 / 中断 / 速率限制调度
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import logging
import os
import random
import time
from typing import Any, Dict, Iterable, List, Optional, Sequence

logger = logging.getLogger("bersona.llm")


class LLMClientError(RuntimeError):
	"""统一的 LLM 客户端异常。"""


@dataclass
class LLMCallResult:
	model: str
	text: str
	duration_ms: float
	prompt_tokens: Optional[int] = None
	completion_tokens: Optional[int] = None
	error: Optional[str] = None


# 简易 metrics 聚合器（进程级）
_METRICS: Dict[str, Any] = {
	"calls": 0,
	"success": 0,
	"fail": 0,
	"retries": 0,
	"fallback_activations": 0,
	"model_durations_ms": {},  # model -> list[float]
}


def collect_llm_metrics() -> Dict[str, Any]:
	"""返回 metrics 的浅拷贝。"""
	# 不做深拷贝 list，外部只读即可
	return dict(_METRICS)


# ---------------- Provider 抽象与实现 ---------------- #
class BaseProvider:
	name = "base"

	def complete(
		self,
		prompt: str,
		*,
		model: str,
		temperature: float,
		max_tokens: int,
		timeout: Optional[float],
	) -> LLMCallResult:
		raise NotImplementedError


class StubProvider(BaseProvider):
	name = "stub"

	def complete(
		self,
		prompt: str,
		*,
		model: str,
		temperature: float,
		max_tokens: int,
		timeout: Optional[float],
	) -> LLMCallResult:
		start = time.time()
		# 模拟轻微随机扰动，避免测试中把 stub 与缓存混淆（可选）
		_ = (prompt, temperature, max_tokens, timeout)
		text = (
			'{"core_identity":"结构化占位","motivation":"结构化占位",'
			'"decision_style":"结构化占位","social_style":"结构化占位",'
			'"strength_traits":["占位A","占位B"],"growth_opportunities":["占位改进"],"advanced":{}}'
		)
		return LLMCallResult(model=model, text=text, duration_ms=(time.time() - start) * 1000)


class OpenAIProvider(BaseProvider):  # 仅在可用时使用
	name = "openai"

	def __init__(self):
		try:
			import openai  # type: ignore
		except Exception as e:  # pragma: no cover - 环境缺失时路径
			raise LLMClientError(
				f"OpenAIProvider 初始化失败：{e}. 请安装 openai 并配置 OPENAI_API_KEY"
			)
		self._openai = openai
		# 新版 openai SDK (>=1.0) 客户端
		if hasattr(openai, "OpenAI"):
			self._client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
		else:  # 兼容旧版
			self._client = openai

	def complete(
		self,
		prompt: str,
		*,
		model: str,
		temperature: float,
		max_tokens: int,
		timeout: Optional[float],
	) -> LLMCallResult:
		start = time.time()
		try:
			# 兼容新旧接口（示例实现，不做复杂分支）
			if hasattr(self._client, "chat") and hasattr(self._client.chat, "completions"):
				resp = self._client.chat.completions.create(
					model=model,
					messages=[{"role": "user", "content": prompt}],
					temperature=temperature,
					max_tokens=max_tokens,
				)
				choice = resp.choices[0]
				text = choice.message.content or ""
				usage = getattr(resp, "usage", None)
				pt = getattr(usage, "prompt_tokens", None) if usage else None
				ct = getattr(usage, "completion_tokens", None) if usage else None
			elif hasattr(self._client, "ChatCompletion"):
				resp = self._client.ChatCompletion.create(
					model=model,
					messages=[{"role": "user", "content": prompt}],
					temperature=temperature,
					max_tokens=max_tokens,
				)
				text = resp["choices"][0]["message"]["content"]
				usage = resp.get("usage")
				pt = usage.get("prompt_tokens") if usage else None
				ct = usage.get("completion_tokens") if usage else None
			else:  # pragma: no cover - 未来 SDK 变更
				raise RuntimeError("未知的 openai SDK 接口形式")

			return LLMCallResult(
				model=model,
				text=text,
				duration_ms=(time.time() - start) * 1000,
				prompt_tokens=pt,
				completion_tokens=ct,
			)
		except Exception as e:  # noqa: BLE001
			return LLMCallResult(
				model=model,
				text="",
				duration_ms=(time.time() - start) * 1000,
				error=str(e),
			)


def _select_provider(model_name: str) -> BaseProvider:
	if model_name.startswith("stub"):
		return StubProvider()
	# 若包含 openai 常见前缀
	if any(model_name.startswith(p) for p in ("gpt-", "o1", "o3", "text-")):
		try:
			return OpenAIProvider()
		except LLMClientError as e:
			logger.warning("OpenAIProvider 不可用，降级 stub: %s", e)
			return StubProvider()
	# 默认回退 stub
	return StubProvider()


def _exponential_backoff(attempt: int, base: float = 0.6, jitter: float = 0.2) -> None:
	delay = base * (2 ** (attempt - 1))
	delay += random.random() * jitter
	time.sleep(min(delay, 4.0))  # 限制最大等待


def generate_json(
	prompt: str,
	*,
	model: str = "stub-1",
	temperature: float = 0.3,
	max_tokens: int = 800,
	timeout: float | None = 40.0,
	max_retries: int = 2,
	fallback_models: Optional[Sequence[str]] = None,
	raise_on_failure: bool = True,
	capture_stats: Optional[Dict[str, Any]] = None,
) -> str:
	"""调用 LLM 返回文本（预期 JSON）。

	重试策略：
	  - 对当前模型尝试 max_retries + 1 次；若仍失败且存在 fallback_models，则切换下一个。
	  - 失败判定：返回为空或包含 error。

	参数：
	  prompt: 拼装后的完整 Prompt。
	  model: 主模型名称。
	  fallback_models: 备用模型列表（按顺序）。
	  raise_on_failure: 若所有尝试失败，是否抛异常；否则返回 stub JSON。
	"""

	start_total = time.time()
	models_chain: List[str] = [model] + list(fallback_models or [])
	last_error: Optional[str] = None

	attempts_total = 0
	for mi, m in enumerate(models_chain):
		provider = _select_provider(m)
		for attempt in range(1, max_retries + 2):  # attempt 从 1 开始
			attempts_total += 1
			_METRICS["calls"] += 1
			if attempt > 1:
				_METRICS["retries"] += 1
			if mi > 0 and attempt == 1:
				_METRICS["fallback_activations"] += 1
			result = provider.complete(
				prompt,
				model=m,
				temperature=temperature if attempt == 1 else max(0.0, temperature - 0.2),
				max_tokens=max_tokens,
				timeout=timeout,
			)
			_METRICS.setdefault("model_durations_ms", {}).setdefault(m, []).append(result.duration_ms)

			if result.error or not result.text.strip():
				last_error = result.error or "empty_response"
				logger.warning(
					"LLM 调用失败 model=%s attempt=%d error=%s", m, attempt, last_error
				)
				if attempt <= max_retries:
					_exponential_backoff(attempt)
					continue
				break  # 当前模型放弃，进入下一个 fallback
			# 成功
			_METRICS["success"] += 1
			if capture_stats is not None:
				capture_stats.update(
					{
						"final_model": m,
						"model_index": mi,
						"attempts": attempts_total,
						"retries": attempts_total - 1,
						"prompt_tokens": result.prompt_tokens,
						"completion_tokens": result.completion_tokens,
					}
				)
			return result.text
		# 当前模型彻底失败，继续 fallback（如果有）
	_METRICS["fail"] += 1

	fail_msg = f"所有模型调用失败: chain={models_chain} last_error={last_error}"
	if capture_stats is not None:
		capture_stats.update(
			{
				"final_model": None,
				"model_index": None,
				"attempts": attempts_total,
				"retries": attempts_total - 1,
				"prompt_tokens": None,
				"completion_tokens": None,
				"error": last_error,
			}
		)
	if raise_on_failure:
		raise LLMClientError(fail_msg)
	logger.error(fail_msg + " -> 返回 stub JSON 作为降级")
	# 最终兜底：返回最小结构 JSON
	return (
		'{"core_identity":"fallback","motivation":"fallback",'
		'"decision_style":"fallback","social_style":"fallback",'
		'"strength_traits":["resilient"],"growth_opportunities":["refine details"],"advanced":{}}'
	)


__all__ = [
	"generate_json",
	"LLMClientError",
	"collect_llm_metrics",
	"LLMCallResult",
]

