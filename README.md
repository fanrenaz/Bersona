# Bersona 星盘生成

一个使用 Skyfield (以及可选 Swiss Ephemeris) 生成西方占星出生星盘的 Python 核心类。现已采用 Pydantic 2 模型定义输入与输出。

## 特性
- 行星位置：Sun, Moon, Mercury, Venus, Mars, Jupiter, Saturn, Uranus, Neptune, Pluto 黄道经纬度（自动使用 Skyfield 星历）
- 上升星座 (Ascendant)
- 宫位系统：等宫制 (Equal)；若安装 `pyswisseph` 可使用 Placidus
- 星座归属与主宰行星（传统 / 现代 可选）
- 行星逆行标记：基于前一日黄经差值判断
- 主要相位：合相(0°)、六分(60°)、四分(90°)、三分(120°)、对分(180°)；支持自定义 orb
- 互溶接纳 (Mutual Reception)：检测两行星位于彼此主宰星座内
- 工具函数：
  - 时间解析 `parse_birth_datetime` 支持多格式 & 中文日期
  - 城市坐标获取 `get_city_coordinates` 支持中文/英文/拼音 (加载 `data/cn_cities.json` 可扩展)
  - 行政区解析 `parse_admin_location` + 在线地理编码 `geocode_china_location` (基于 OpenStreetMap Nominatim)
- LLM 占星解释: 使用 `astrology_describe(chart)` 基于全量星盘数据调用 LLM 生成占星文字内容

## 默认行为与输入规范
`Bersona.generate_chart` 目前内置以下默认与自动处理逻辑：
1. 默认地理坐标为北京：纬度 39.9042，经度 116.4074；若未显式传入 `latitude` / `longitude` 则使用此值。
2. 出生时间输入可为多种格式 (字符串 / 时间戳 / datetime)：
  - 英文/数字：`1990-05-17 14:30`, `1990/05/17 14:30`, `1990-05-17` (仅日期)
  - 中文：`1990年5月17日14时30分`, `1990年5月17日`
  - Unix 时间戳：如 `643708200`
3. 若输入“仅日期” (无时间部分)，自动补全为当地时间中午 12:00:00（示例：`1990-05-17` -> `1990-05-17 12:00:00 +08:00`）。
4. 对于 naive datetime 或无时区字符串，统一默认赋予 `+08:00`（中国标准时间）。
5. 仅日期输入会在内部标记 `ChartInput.date_only=True`；星盘仍计算所有行星与相位，但不计算上升与宫位（`ascendant=None`, `houses=[]`）。

可接受的字符串示例：
```
1990-05-17 14:30
1990/05/17 14:30
1990年5月17日14时30分
1990-05-17        # 自动 -> 1990-05-17 12:00:00 +08:00
1990年5月17日     # 自动 -> 1990-05-17 12:00:00 +08:00
643708200         # 时间戳 -> 1990-05-17 06:30:00 UTC 再转换为 +08:00
```

最简示例（使用默认北京与日期自动补全）：
```python
from Bersona import Bersona
astro = Bersona()
chart = astro.generate_chart('1990-05-17')  # -> 中午 12:00 默认北京
print(chart.input.birth_datetime)            # 1990-05-17 12:00:00+08:00
print(chart.ascendant.sign)
print(chart.input.date_only)  # True 表示原始输入为仅日期

### 日期与日期时间对比
```python
from Bersona import Bersona
b = Bersona()
chart_dt = b.generate_chart('1990-05-17 14:30')
chart_date = b.generate_chart('1990-05-17')
print('date-only flag:', chart_date.input.date_only)  # True
print('ascendant (date-time):', chart_dt.ascendant.sign)
print('ascendant (date-only):', chart_date.ascendant)  # None
print('planets count compare:', len(chart_dt.planets), len(chart_date.planets))
print('aspects count compare:', len(chart_dt.aspects), len(chart_date.aspects))
```
```
# 行政区格式 -> 坐标示例
from Bersona.utils import parse_admin_location, geocode_china_location
loc = parse_admin_location('浙江省杭州市')  # {'province': '浙江省', 'city': '杭州'}
lat_lon = geocode_china_location('浙江省杭州市')
print(lat_lon)
chart3 = astro.generate_chart(birth_dt, latitude=lat_lon[0], longitude=lat_lon[1])


## 安装
```bash
pip install -r requirements.txt
```
可选安装更高精度星历：
```python
from skyfield.api import load
load('de440.bsp')  # 替换默认的 de421.bsp
```

### 星历文件自动下载说明
本项目不再随仓库附带 `de421.bsp`。运行时若本地缓存目录（默认 `~/.skyfield` 或自定义 `SKYFIELD_CACHE_DIR`）中不存在所需星历文件，会首次自动下载：

- 默认：`de421.bsp` 约 20MB
- 可选更高精度：设置环境变量 `BERSONA_EPHEMERIS=de440s.bsp`（约 120MB）或其他合法星历文件名

首次下载时会在控制台提示：
```
[Bersona] 首次使用星历 'de421.bsp'，将自动下载约 20MB，需保持网络畅通...
```

自定义缓存目录：
```bash
export SKYFIELD_CACHE_DIR="/path/to/.skyfield-cache"
```

选择不同星历文件：
```bash
export BERSONA_EPHEMERIS="de440s.bsp"
```

若需完全离线运行，请预先在可联网环境执行一次加载以缓存文件，然后复制缓存目录到目标机器。

## 使用示例
# 城市坐标与时间解析示例
from Bersona.utils import parse_birth_datetime, get_city_coordinates
dt = parse_birth_datetime('1990年5月17日14时30分')
lat, lon = get_city_coordinates('上海')  # (31.2304, 121.4737)
chart2 = astro.generate_chart(dt, latitude=lat, longitude=lon)

```python
from datetime import datetime
import zoneinfo
from Bersona import Bersona  # 安装 / 在父目录添加到 sys.path 后即可

birth_dt = datetime(1990, 5, 17, 14, 30, tzinfo=zoneinfo.ZoneInfo('Asia/Shanghai'))
astro = Bersona()
chart = astro.generate_chart(
  birth_dt,
  latitude=31.2304,
  longitude=121.4737,
  house_system='placidus',
  aspect_orbs={
    'Conjunction': 8,
    'Opposition': 8,
    'Trine': 7,
    'Square': 6,
    'Sextile': 4,
  },
  rulers_scheme='modern'
)

# Pydantic 模型：可直接访问字段
print(chart.ascendant.sign)
print(chart.planets['Sun'].ecliptic_longitude)
print(chart.summary())

# 导出 JSON
print(chart.model_dump_json(indent=2, ensure_ascii=False))
```

## LLM 集成 (可选)
`Bersona` 初始化时会尝试基于以下环境变量建立一个 OpenAI 兼容客户端：

环境变量：
- `OPENAI_API_KEY` 或 `OPENAI_KEY`: API 密钥（必需）
- `OPENAI_BASE_URL`: 自定义基地址，用于兼容代理 / 第三方服务（可选）
- `OPENAI_MODEL`: 默认模型名称（可选，若未设置需在调用时显式提供）

示例：
```bash
export OPENAI_API_KEY="sk-xxxx"  # 或 OPENAI_KEY
export OPENAI_MODEL="gpt-4o-mini"
```

调用：
```python
from Bersona import Bersona
b = Bersona()
if b.llm_available:
  reply = b.llm_chat([
    {"role": "system", "content": "你是一个星盘解读助手"},
    {"role": "user", "content": "请简要解释我的太阳在双子座意味着什么"}
  ])
  print(reply)
else:
  print("LLM 不可用，检查是否设置了 OPENAI_API_KEY")
```

返回值：
- 成功：模型第一条消息文本
- 失败或未配置：`None`

注意：
- 未设置密钥不会报错，`b.llm_available` 为 False。
- 若使用 Azure / 本地镜像等兼容服务，请设置 `OPENAI_BASE_URL`。
- 仅做最简封装，复杂对话管理请自行扩展。

### 星盘解释 `astrology_describe`
该方法将整个 `ChartResult` 结构序列化为纯文本（通过内部工具 `chart_to_text`），并结合语言对应的系统提示模板 (`prompts.py` 中 `BASE_PROMPTS`) 向 LLM 发送消息，获得专业占星解释。

示例：
```python
from Bersona import Bersona
astro = Bersona()
chart = astro.generate_chart('1990-05-17 14:30')
desc = astro.astrology_describe(chart, language='zh')  # 需已设置 OPENAI_API_KEY
print(desc.text)
```

`AstrologyDesc` 模型字段：
- `text`: LLM 返回的完整占星解释
- `model_used`: 使用的模型名称
- `created_at`: UTC 创建时间
- `language`: 语言代码
- `chart_snapshot`: 当前版本为空字典（预留后续扩展）

约束：
- 若未配置密钥或 LLM 调用失败直接抛出异常，不提供占位回退。
- 文本长度与风格可通过自定义 prompts 扩展（修改 `prompts.py`）。

### 自定义提示模板
编辑 `prompts.py` 中的 `BASE_PROMPTS` 可调整输出风格、结构、语气。可增加键如 `"zh-long"` 或 `"en-brief"`，调用时通过 `language='zh-long'` 选择。

### 内部工具 `chart_to_text`
该函数将星盘核心数据行格式化为文本块并传入 LLM，暂不建议直接对终端用户展示（缺乏解释语义）。可根据需要做进一步美化或转换为 Markdown 表格。

## 常见问题 (FAQ)
Q: 调用 `astrology_describe` 报错 "LLM 不可用"?\nA: 未设置 `OPENAI_API_KEY` 或网络/代理不可达。请配置环境变量并重试。

Q: 如何更换模型?\nA: 设置环境变量 `OPENAI_MODEL` 或在调用时传参 `model='gpt-4o-mini'`。

Q: 想输出英文?\nA: 传入 `language='en'`，或扩展 `prompts.py` 添加新键。

Q: 能否流式输出?\nA: 当前封装未支持，可直接调用底层 `self._llm_client.chat.completions.create(stream=True, ...)` 自行扩展。

Q: chart_snapshot 为什么为空?\nA: 预留 future 扩展（例如提炼关键信息 JSON），当前全部数据直接在 prompt 中传递无需再重复保存。

## 返回数据结构说明
```json
{
  "input": {"birth_datetime": "...", "latitude": ..., "longitude": ..., "date_only": false},
  "settings": {
    "house_system": "equal|placidus",
    "rulers_scheme": "traditional|modern",
    "aspect_orbs": {"Conjunction":8,...},
    "libraries": {"skyfield": true, "pyswisseph": true}
  },
  "ascendant": {"longitude": 123.45, "sign": "Leo"},
  "houses": [
    {"house":1, "cusp_longitude":123.45, "cusp_sign":"Leo"},
    ...
  ],
  "planets": {
    "Sun": {"ecliptic_longitude": 56.7, "ecliptic_latitude": 0.2, "sign": "Gemini", "retrograde": false},
    ...
  },
  "aspects": [
    {"planet1":"Sun","planet2":"Moon","aspect":"Square","separation":90.3,"difference":0.3,"orb_allowed":6.0},
    ...
  ],
  "mutual_receptions": [
    {"planet1":"Venus","planet2":"Mars","scheme":"traditional","signs":["Aries","Taurus"]}
  ]
}
```

## 注意事项 / 限制
- 若未安装 Skyfield，将使用占位逻辑，精度极低，仅用于结构演示。
- Placidus 需要 `pyswisseph`；安装后自动启用（参数为 'placidus'）。若计算异常，会自动回退到等宫制。
- 逆行判断采用前一日黄经差值的简单符号法，未考虑站点日细节。
- 城市数据集仅示例，若需覆盖全部中国行政区，请扩展 `data/cn_cities.json` 或集成外部地理库（如高德/百度 API，或离线行政区数据）。
- 在线地理编码使用 OpenStreetMap Nominatim，有速率限制，批量请求需添加延迟。建议缓存结果或使用本地离线库。

## 后续改进建议
- 加入月亮交点、凯龙星等扩展天体
- 更多相位（半刑、梅花等）与容许度分行星类型调整
- 本命与运行对照盘 (Transit) 支持
- 日/时行星守护、行星尊贵（四表：旺、陷、庙、失势）

## 许可
本仓库当前未附加特定 License，请在使用前补充适当开源许可文本。
