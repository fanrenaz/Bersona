# ...migrated content...
"""占星解释 LLM 提示模板。

提供不同语言的基础系统提示。后续可扩展分层/风格/长度参数。
"""
from typing import Dict

__all__ = ["BASE_PROMPTS"]

BASE_PROMPTS: Dict[str, str] = {
    "zh": (
        "请基于后续提供的完整本命星盘原始数据，输出结构化且自然流畅的中文解释。"
        "需要描述这个人的性格、特质、喜好、职业方向等个人方面的特征，以及可能会感兴趣的媒体内容类型和风格。"
        "需要隐藏关于占星术语的表达，让这个描述能让普通人看懂。正面与反面的信息都需要包含。"
        "输出部分用```ASTROLOGY_DESC_START```和```ASTROLOGY_DESC_END```包裹。"
    ),
    "en": (
        "Using the full natal chart raw data provided, produce a structured yet fluid English interpretation."
        "Describe the person's personality, traits, preferences, career directions, and types and styles of media content they might be interested in."
        "Avoid astrological jargon, making the description accessible to a general audience. Include both positive and negative aspects."
        "Wrap the output section with ```ASTROLOGY_DESC_START``` and ```ASTROLOGY_DESC_END```."
    ),
}
