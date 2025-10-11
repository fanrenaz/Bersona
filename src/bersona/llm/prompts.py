"""Prompt 模板集合。

当前实现：结构化层 (Structuring Layer) 的 Prompt 模板：`STRUCTURE_PROMPT_TEMPLATE`。

设计原则：
1. 显式角色指令：强调“符号学 → 现代心理/行为特征翻译专家”。
2. 严格输出约束：必须返回单个 JSON，不添加解释性文字 / Markdown。
3. Few-shot: 仅提供占星（太阳星座）最小示例，引导字段风格与粒度。
4. 语言：暂使用中文说明 + 输出字段中文语义但字段 key 为英文，方便后续国际化。
5. 容错提示：若信息不足应合理概括，不得捏造不存在的符号。

下游解析策略：直接截取第一个 JSON 对象；若失败再 fallback。
"""

from __future__ import annotations

from textwrap import dedent

STRUCTURE_PROMPT_TEMPLATE = dedent(
		r"""
你是一个严谨的“符号学人格特征结构化专家”。任务：
将输入的【原始符号数据】翻译为统一、结构化、机器友好的画像特征 JSON。不要输出除 JSON 以外的任何字符（包括前后缀说明、Markdown、注释、代码块标记）。

【字段定义】(所有字段均为必需；若缺失或无法确定，给出合适的概括，不留空字符串)：
{
	"core_identity": "一句高度概括该个体内在核心特质 (<= 20 汉字)",
	"motivation": "主要内在驱动力 / 价值追求 (<= 20 汉字)",
	"decision_style": "决策风格（示例：逻辑、分析、直觉、情感平衡、务实 等）",
	"social_style": "社交表达方式（示例：克制、外向、沉稳、热情、观察型 等）",
	"strength_traits": ["优势特质关键词，2~6 个，单词或短词，避免重复"],
	"growth_opportunities": ["成长机会/易出现的偏差或盲点，1~4 个，具体、可操作"],
	"advanced": {"可选的高级符号展开": "若无则可省略或使用{}"}
}

【风格要求】:
1. JSON 必须合法、UTF-8、无注释、字段顺序不强制。
2. 不使用“可能”、“也许”堆砌；保持中性、专业、紧凑。
3. 不做心理诊断，不输出迷信化措辞；使用行为/倾向语言。
4. 不捏造未在符号中出现的高阶概念。

【输入原始符号数据】:
{raw_symbols_json}

如果输入中缺少某些可选高级符号（如 ascendant_sign, moon_sign），不要臆造。

【输出示例 (Few-shot)】(示例仅供风格参考，不能照搬)：
示例1（占星 - 仅太阳星座 Virgo） =>
INPUT_SYMBOLS={"astrology_raw": {"sun_sign": "Virgo"}}
OUTPUT_JSON={
	"core_identity": "细致分析与改进导向",
	"motivation": "通过解决实际问题带来秩序与价值",
	"decision_style": "逻辑与证据优先",
	"social_style": "克制而礼貌",
	"strength_traits": ["分析力","责任感","改进意识"],
	"growth_opportunities": ["避免过度苛求","提升容错弹性"],
	"advanced": {}
}

【现在开始】请直接输出唯一 JSON：
"""
)

__all__ = ["STRUCTURE_PROMPT_TEMPLATE"]

BATCH_STRUCTURE_PROMPT_TEMPLATE = dedent(
		r"""
你是一个严谨的“符号学人格特征结构化专家”。现在需要对一组输入进行批量结构化。
返回 JSON 数组，每个元素与输入序号一一对应。

【输出数组说明】:
[
	{ 单个对象结构 (同单条结构化定义) },
	{ ... },
	...
]

字段同单条定义，要求与单条模板一致。数组长度必须与输入条目数相同。不要输出除该 JSON 数组以外的任何字符。

【输入原始符号数据列表】:
{raw_symbols_batch_json}

示例（仅结构示意，不可复用内容）:
INPUT=[{"astrology_raw": {"sun_sign": "Virgo"}}, {"astrology_raw": {"sun_sign": "Aries"}}]
OUTPUT=[
	{
		"core_identity": "细致分析与改进导向",
		"motivation": "通过解决实际问题带来秩序与价值",
		"decision_style": "逻辑与证据优先",
		"social_style": "克制而礼貌",
		"strength_traits": ["分析力","责任感","改进意识"],
		"growth_opportunities": ["避免过度苛求","提升容错弹性"],
		"advanced": {}
	},
	{
		"core_identity": "行动驱动与尝试导向",
		"motivation": "启动新事物并取得快速进展",
		"decision_style": "直接与快速",
		"social_style": "外向坦率",
		"strength_traits": ["勇气","执行","开拓"],
		"growth_opportunities": ["耐心培养"],
		"advanced": {}
	}
]

【现在开始】请直接输出唯一 JSON 数组：
"""
)

__all__.append("BATCH_STRUCTURE_PROMPT_TEMPLATE")

