"""Fallback 策略 (TODO 1.2 - 3.5)。

当 LLM 结构化阶段：
 - 调用失败 (网络/限流/模型错误)
 - 解析失败 (JSON 损坏 / 字段缺失严重)
 - 或者策略层主动降级 (成本/速率限制)

则使用启发式 *最小可用画像*，确保上游系统永远获得结构化输出。

原则：
1. 只依赖已计算出的原始符号（不做额外推断）。
2. 输出字段全部填充（满足 Schema 必需字段），未覆盖部分保持“适度概括”；用词中性、可操作，避免宿命化。
3. 保证 deterministic（同一符号 → 同一输出），便于缓存与评估。

当前支持：
 - 占星太阳星座 sun_sign

扩展：未来可分离词库 JSON，并允许社区 PR 调整描述。
"""

from __future__ import annotations

from typing import Dict, Any, Tuple

from .schemas import StructuredPersonaFeatures

SUN_SIGN_MAP: Dict[str, Dict[str, Any]] = {
    # 简洁两到三个词语/短语；优势 traits 尽量抽象度相近，growth 表述为可调整方向
    "Aries": {
        "core_identity": "行动驱动与尝试导向",
        "motivation": "启动新事物并取得快速进展",
        "decision_style": "直接与快速",
        "social_style": "外向坦率",
        "strengths": ["勇气", "执行", "开拓"],
        "growth": ["耐心培养"],
    },
    "Taurus": {
        "core_identity": "稳定持久与价值积累",
        "motivation": "构建可持续与有形收益",
        "decision_style": "稳健务实",
        "social_style": "温和克制",
        "strengths": ["耐力", "踏实", "感知细节"],
        "growth": ["适度灵活"],
    },
    "Gemini": {
        "core_identity": "信息交换与多元好奇",
        "motivation": "获取与分发新鲜信息",
        "decision_style": "快速对比",
        "social_style": "机敏善聊",
        "strengths": ["适应", "沟通", "多角度"],
        "growth": ["聚焦深化"],
    },
    "Cancer": {
        "core_identity": "情绪敏感与保护倾向",
        "motivation": "建立安全与归属",
        "decision_style": "情境感知",
        "social_style": "体贴含蓄",
        "strengths": ["关怀", "记忆力", "直觉"],
        "growth": ["界限清晰"],
    },
    "Leo": {
        "core_identity": "表现驱动与自我表达",
        "motivation": "获得认可与影响力",
        "decision_style": "自信直观",
        "social_style": "热情外放",
        "strengths": ["领导", "鼓舞", "自信"],
        "growth": ["倾听比率"],
    },
    "Virgo": {
        "core_identity": "细致分析与改进聚焦",
        "motivation": "通过优化提升价值",
        "decision_style": "逻辑拆分",
        "social_style": "克制审慎",
        "strengths": ["分析", "责任", "改进"],
        "growth": ["避免过度挑剔"],
    },
    "Libra": {
        "core_identity": "平衡协调与审美取向",
        "motivation": "促成合作与和谐",
        "decision_style": "权衡多方",
        "social_style": "圆融友好",
        "strengths": ["协调", "关系感", "审美"],
        "growth": ["果断训练"],
    },
    "Scorpio": {
        "core_identity": "深度洞察与聚焦韧性",
        "motivation": "探究核心与掌控变量",
        "decision_style": "隐性分析",
        "social_style": "审视内敛",
        "strengths": ["洞察", "专注", "韧性"],
        "growth": ["释放紧张"],
    },
    "Sagittarius": {
        "core_identity": "探索扩展与意义追寻",
        "motivation": "拓展视野与抽象理解",
        "decision_style": "宏观直觉",
        "social_style": "开放乐观",
        "strengths": ["远景", "学习", "乐观"],
        "growth": ["细节跟进"],
    },
    "Capricorn": {
        "core_identity": "结构目标与自律攀升",
        "motivation": "实现长期成就",
        "decision_style": "策略规划",
        "social_style": "克制稳重",
        "strengths": ["执行持续", "规划", "责任"],
        "growth": ["灵活调整"],
    },
    "Aquarius": {
        "core_identity": "独立思考与系统革新",
        "motivation": "引入新模型与改良",
        "decision_style": "抽象评估",
        "social_style": "理性疏离",
        "strengths": ["创新", "系统感", "客观"],
        "growth": ["情感连接"],
    },
    "Pisces": {
        "core_identity": "共情融合与想象流动",
        "motivation": "情感共鸣与创意表达",
        "decision_style": "直觉感受",
        "social_style": "柔性包容",
        "strengths": ["共情", "想象", "适应"],
        "growth": ["边界清晰"],
    },
}


# 已移除八字日主映射（项目聚焦占星）。


def build_fallback_persona(raw_symbols: dict) -> StructuredPersonaFeatures:
    """根据 raw_symbols 构造最小可用 persona。

    优先级：
      1. astrology_raw.sun_sign
    若不存在 -> 返回全部 unknown + 空列表。
    """
    sun_sign = (
        (raw_symbols.get("astrology_raw") or {}).get("sun_sign")
        if isinstance(raw_symbols, dict)
        else None
    )

    if isinstance(sun_sign, str) and sun_sign in SUN_SIGN_MAP:
        template = SUN_SIGN_MAP[sun_sign]
        return StructuredPersonaFeatures.create_minimal(
            core_identity=template["core_identity"],
            motivation=template["motivation"],
            decision_style=template["decision_style"],
            social_style=template["social_style"],
            strengths=template["strengths"][:2],
            growth=template["growth"][:1],
            raw_symbols=raw_symbols,
            incomplete_fields=[],
            fallback=True,
        )

    return StructuredPersonaFeatures.create_minimal(
        core_identity="初始概括缺失",
        motivation="初始概括缺失",
        decision_style="unknown",
        social_style="unknown",
        strengths=["适应"],
        growth=["信息补充"],
        raw_symbols=raw_symbols,
        incomplete_fields=["core_identity", "motivation"],
        fallback=True,
    )


__all__ = ["build_fallback_persona", "SUN_SIGN_MAP"]
