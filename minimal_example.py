"""最简 Bersona 使用示例

仅演示: 创建 Bersona -> 生成星盘 -> 打印结果摘要。
无需命令行参数，直接修改脚本内的出生时间与经纬度即可。
"""
from datetime import datetime
import zoneinfo
from bersona import Bersona
import logging
import os

import dotenv
dotenv.load_dotenv()  # 从 .env 文件加载环境变量（如果存在）

logger = logging.getLogger("bersona")
if not logger.handlers:
    _handler = logging.StreamHandler()
    _formatter = logging.Formatter("[%(asctime)s] %(levelname)s %(name)s: %(message)s")
    _handler.setFormatter(_formatter)
    logger.addHandler(_handler)
log_level = os.getenv("BERSONA_LOG_LEVEL", "INFO").upper()
try:
    logger.setLevel(getattr(logging, log_level, logging.INFO))
except Exception:
    logger.setLevel(logging.INFO)

# 1. 准备带时区的出生时间 (示例: 1990-05-17 14:30, 上海时区)
tz = zoneinfo.ZoneInfo("Asia/Shanghai")
birth_dt = datetime(1997, 10, 14, 17, 10, tzinfo=tz)

# 3. 创建对象并生成星盘
b = Bersona()
chart = b.generate_chart(birth_dt)

# 4.若已设置 OPENAI_API_KEY 则生成占星描述
if b.llm_available:
	try:
		desc = b.astrology_describe(chart, language='zh')
		print("\nLLM 描述:")
		print(desc)
	except Exception as e:
		print(f"[LLM 错误] {e}")
else:
	print("(未检测到 OPENAI_API_KEY，跳过 LLM 描述)")
