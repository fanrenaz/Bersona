<div align="center">

# Bersona

精准西方占星本命星盘生成与 LLM 解释引擎。

<p>
<strong>Generate natal charts (Sun..Pluto, Ascendant, Houses, Aspects, Mutual Receptions) and obtain structured AI interpretations.</strong>
</p>

<p>
<img alt="python" src="https://img.shields.io/badge/Python-3.10%2B-blue" />
<img alt="license" src="https://img.shields.io/badge/License-MIT-green" />
<img alt="status" src="https://img.shields.io/badge/status-alpha-orange" />
</p>

</div>

## 1. 简介 (Overview)
`Bersona` 提供本命星盘核心计算与基于 LLM 的自动解释。核心依赖 Skyfield（高精度行星位置），可选 PySwissEph（Placidus 宫位），并以 Pydantic 2 定义结构化数据模型，方便序列化与集成。

应用场景：
- 在线占星应用 / 微信小程序 / Web 后端服务
- 星盘计算微服务或批量数据处理
- 将星盘结构转接入 LLM 进行定制风格解读

## 2. 主要特性 (Features)
- 行星位置：Sun, Moon, Mercury, Venus, Mars, Jupiter, Saturn, Uranus, Neptune, Pluto
- 宫位系统：Equal；安装 `pyswisseph` 自动支持 Placidus
- 上升星座 (Ascendant)
- 主要相位：0° / 60° / 90° / 120° / 180°，支持自定义容许度 (orb)
- 逆行标记：通过前一日黄经差异简单判定
- 互溶接纳 (Mutual Reception)：传统 / 现代主宰体系可选
- 多格式出生时间解析：ISO, 简化, 中文日期, 时间戳
- 可选地理编码：行政区解析 + Nominatim（需要网络）
- LLM 解释：基于完整星盘文本提示生成自然语言描述，可自定义 system prompt

## 3. 安装 (Installation)
核心最小安装：
```bash
pip install .
```
全部可选功能：
```bash
pip install .[all]
```
分组安装：
```bash
pip install .[placidus]
pip install .[llm]
pip install .[geocode]
pip install .[dev]  # 测试依赖 (pytest)
```

## 4. 快速开始 (Quick Start)
```python
from bersona import Bersona
from datetime import datetime
import zoneinfo

tz = zoneinfo.ZoneInfo('Asia/Shanghai')
dt = datetime(1990, 5, 17, 14, 30, tzinfo=tz)
astro = Bersona()
chart = astro.generate_chart(dt, latitude=31.2304, longitude=121.4737, house_system='placidus')
print(chart.summary())
```

LLM 解释：
```python
if astro.llm_available:
    desc = astro.astrology_describe(chart, language='zh', system_prompt='你是一位温暖且专业的占星导师，请分段解释：')
    print(desc.text)
```

## 5. 数据模型 (Data Models)
核心 Pydantic 模型：
- `ChartInput` / `ChartSettings` / `ChartResult`
- `Ascendant` / `HouseCusp` / `PlanetPosition` / `Aspect` / `MutualReception`
- `AstrologyDesc` (LLM 输出包装)

示例：
```python
from bersona.models import ChartResult
print(chart.planets['Sun'].ecliptic_longitude)
print(chart.aspects[0].aspect)
print(chart.model_dump())
```

## 6. 时间输入支持 (Date Parsing)
`parse_birth_datetime` 支持：
- `1990-05-17 14:30:00`, `1990/05/17 14:30`
- 中文：`1990年5月17日14时30分`
- 仅日期：`1990-05-17` 自动补中午 12:00 并标记 `date_only=True`
- 时间戳：`643708200`

## 7. 环境变量 (Environment Variables)
| 变量 | 说明 | 默认 |
|------|------|------|
| `BERSONA_EPHEMERIS` | 星历文件名 | `de421.bsp` |
| `SKYFIELD_CACHE_DIR` | 自定义缓存目录 | `~/.skyfield` |
| `OPENAI_API_KEY` / `OPENAI_KEY` | LLM API 密钥 | 无 |
| `OPENAI_BASE_URL` | 自定义 OpenAI 接口地址 | 官方地址 |
| `OPENAI_MODEL` | 默认模型名称 | 无 |
| `BERSONA_QUIET` | 关闭下载提示 (1) | 0 |
| `BERSONA_LOG_LEVEL` | 未来日志级别 | `info` |

可复制 `.env.example`：
```bash
cp .env.example .env
source .env
```

## 8. API 摘要 (API Summary)
| 方法 | 说明 | 关键参数 |
|------|------|---------|
| `Bersona.generate_chart` | 生成星盘 | `birth_dt_input`, `latitude`, `longitude`, `house_system` |
| `Bersona.astrology_describe` | LLM 解释 | `chart`, `language`, `system_prompt`, `model` |
| `Bersona.llm_chat` | 低层对话 | `messages`, `model`, `temperature` |
| `utils.chart_to_text` | 星盘序列化文本 | `ChartResult` |
| `utils.parse_birth_datetime` | 输入时间解析 | 多格式字符串/时间戳 |

## 9. 测试 (Testing)
```bash
pip install .[dev]
python -m pytest -q
```
CI 在 push / PR 自动运行多 Python 版本测试与构建。

## 10. 构建与发布 (Build & Release)
构建：
```bash
python -m build
twine check dist/*
```
TestPyPI 发布与验证：
```bash
twine upload --repository-url https://test.pypi.org/legacy/ dist/*
python -m venv .venv-test && source .venv-test/bin/activate
pip install --index-url https://test.pypi.org/simple --extra-index-url https://pypi.org/simple bersona
```
正式发布（自动）：打 tag `vX.Y.Z` 触发 `release.yml` 使用 `PYPI_API_TOKEN`。

版本号管理：
```bash
python scripts/bump_version.py patch
git tag v$(python -c "import bersona;print(bersona.__version__)")
git push --tags
```

## 11. 版本策略 (Versioning)
语义化版本：`MAJOR.MINOR.PATCH`。
- 初期 (<1.0.0) 频繁变更：提升 MINOR 表示潜在破坏性。
- PATCH：bug 修复或非结构化微改。
- 预发布：可手动设置 `0.x.yrc1` / `0.x.ya1`。

## 12. 贡献指南 (Contributing)
欢迎 Issue 与 PR：
1. Fork & 创建分支：`feature/xxx`
2. 添加/更新测试
3. 运行 `python -m pytest -q`
4. 提交并描述意图与行为变化

建议工具：后续将加入 Ruff/Black；提交前可格式化。

## 13. 路线图 (Roadmap)
- Transit (行运) / Progressions 支持
- 更多天体：凯龙星、黑月莉莉丝、月亮交点
- 高级相位：半刑、梅花等
- 行星尊贵（旺陷庙失势）分析
- LLM 输出结构化 JSON + 可信度指标
- 国际化多语言模板扩展

## 14. License
MIT License © 2025 fanrenaz

## 15. English Quick Glance
```bash
pip install bersona
```
```python
from bersona import Bersona
from datetime import datetime
import zoneinfo
tz = zoneinfo.ZoneInfo('UTC')
chart = Bersona().generate_chart(datetime(1990,5,17,14,30,tzinfo=tz), 40.0, -74.0)
print(chart.summary())
```
LLM description (if API key set):
```python
desc = Bersona().astrology_describe(chart, language='en', system_prompt='You are a concise astrologer:')
print(desc.text)
```

---
欢迎反馈与建议，共同改进 Bersona。
