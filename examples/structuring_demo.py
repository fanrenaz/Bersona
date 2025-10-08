"""结构化层使用示例。

运行：
	python examples/structuring_demo.py

展示内容：
1. 基础调用（stub 模型） → StructuredPersonaFeatures
2. 缓存命中（第二次调用同一 raw_symbols）
3. Metrics 快照（pipeline / cache / llm）
"""

from bersona.structuring.engine import structure_features
from bersona.structuring.metrics import snapshot

RAW_SYMBOLS = {"astrology_raw": {"sun_sign": "Virgo"}, "bazi_raw": {"day_master": "Geng Metal"}}


def main():
	print("First call (cache miss expected):")
	p1 = structure_features(RAW_SYMBOLS, model="stub-1")
	print(p1.model_dump_json(ensure_ascii=False, indent=2))

	print("\nSecond call (cache hit expected):")
	p2 = structure_features(RAW_SYMBOLS, model="stub-1")
	print(p2.model_dump_json(ensure_ascii=False, indent=2))

	print("\nMetrics snapshot:")
	print(snapshot())

	# 简单一致性断言
	assert p1.core_identity == p2.core_identity


if __name__ == "__main__":  # pragma: no cover
	main()
