# Bersona 🧬 生成式占星画像引擎

**只需一个生日，即可解决冷启动问题，生成结构化与语义化的占星用户画像。**

[![PyPI version](https://badge.fury.io/py/bersona.svg)](https://badge.fury.io/py/bersona)
[![许可证: MIT](https://img.shields.io/badge/许可证-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Discord](https://img.shields.io/discord/YOUR_DISCORD_ID?label=加入我们&logo=discord)](https://discord.gg/YOUR_INVITE_LINK)

---

个性化系统在面对新用户时会遭遇 **冷启动问题**：无行为数据 → 难以提供个性化 → 早期体验贫瘠。

**Bersona** 通过用户愿意提供的一个通用信息——**出生日期**（可渐进补充时间与地点）——即时生成占星驱动的结构化画像与自然语言洞察。我们不宣称神秘论，而是把占星本命盘视作一个高维度的“符号标签空间”，使用 LLM 将其转译为机器友好的特征，再生成语义画像。

## ✨ 核心特性（占星聚焦）

* ⚡️ **即时冷启动先验**：仅生日即可获得太阳星座画像，减少初始不确定性。
* 📈 **渐进式保真度**：可选出生时间 + 地点 → 行星、宫位、相位扩展。
* 🧠 **两阶段 LLM 流水线**：结构化层稳定特征，生成层输出多风格语义画像。
* 🏗 **深度而非横向扩展**：聚焦占星单体系，持续提升行星/宫位/相位解释质量与粒度。
* 🤖 **模型无关**：支持 OpenAI / Claude / Mistral / 本地模型；可替换 LLM 客户端。
* 🔒 **隐私优先**：本命盘计算在本地；外发仅抽象符号或结构化特征。
* 💡 **操作性洞察**：不止“天蝎座”，而是“内容偏好：深度叙事、情感真实，避免浅表噪音”。
* 🧪 **缓存与指标**：内置 LRU+TTL 缓存、结构化与生成层调用统计、fallback 比例监控。

## 🚀 快速上手

1.  **安装**
    ```bash
    pip install bersona
    ```

2.  **生成用户画像**
    ```python
    from bersona import Bersona
    import os

    # 使用你首选的 LLM 提供商的 API 密钥初始化客户端
    # 请确保已设置环境变量 OPENAI_API_KEY
    b = Bersona(api_key=os.environ.get("OPENAI_API_KEY"))

    # 1. 仅使用生日，获取基础画像
    baseline_persona = b.get_persona(birth_date="1990-08-25")
    print(baseline_persona)

    # 2. (可选) 提供完整信息，获取高保真画像（含月亮/上升/行星/宫位等）
    # full_persona = b.get_persona(
    #     birth_date="1990-08-25",
    #     birth_time="14:30",
    #     latitude=34.0522,   # 纬度
    #     longitude=-118.2437 # 经度
    # )
    # print(full_persona)
    ```

## 🤔 工作原理（两阶段）

`[用户输入] -> [占星计算内核] -> [LLM 结构化层] -> [LLM 生成层] -> [画像 JSON]`

1. **占星计算内核**：输入出生日期/时间/地点，本地计算原始符号（太阳、月亮、上升、行星星座与宫位）。
   * 示例：`{"astrology_raw": {"sun_sign": "Virgo", "moon_sign": "Cancer", "ascendant": "Libra"}}`
2. **LLM 结构化层**：第一次调用，把符号映射到标准化特征维度（`core_identity`, `motivation`, `decision_style`, ...）以及 `advanced` 扩展字段。
3. **LLM 生成层**：第二次调用，根据结构化特征 + 请求的风格或任务（职业 / 内容偏好 / 关系）生成可读画像。

两阶段设计让生成更稳定：先锁定特征空间，后多样化自然语言表达，降低 Prompt 漂移与冗余。

> 理念：不承诺绝对准确；我们提供的是一个 **优于随机的先验 (Informative Prior)**，帮助系统与团队在冷启动阶段更快收敛。

## 🧩 结构化层 API（Structuring Layer）

结构化层是两阶段流水线的第一跳：输入 “原始符号”(raw symbols)，输出严格受控、机器友好的 `StructuredPersonaFeatures`。这一步保证第二阶段生成层对输入的依赖是稳定且可版本化的。

核心入口函数：`structure_features(raw_symbols: dict, *, model: str = "stub-1", use_cache: bool = True) -> StructuredPersonaFeatures`

最小示例：

```python
from bersona.structuring.engine import structure_features
from bersona.structuring.metrics import snapshot

raw_symbols = {
    "astrology_raw": {"sun_sign": "Virgo"}
}

persona = structure_features(raw_symbols)
print(persona.model_dump_json(ensure_ascii=False, indent=2))

print("Metrics snapshot:")
print(snapshot())  # 包含 pipeline / cache / llm 聚合指标
```

主要字段（V1 Schema）：
- `core_identity`: 核心自我/主题（短句）
- `motivation`: 主要驱动力
- `decision_style`: 决策偏好
- `social_style`: 社交互动风格
- `strength_traits`: 优势特质列表 (<=8)
- `growth_opportunities`: 成长机会列表 (<=6)
- `advanced`: 预留扩展字典（高保真符号映射）
- `fallback`: 是否使用了降级/启发式路径
- `incomplete_fields`: 本次输出中被填补默认值的字段名
- `schema_version` / `generated_at`: 版本与时间戳

容错与降级：
1. LLM 调用异常 / 超时 → 直接启发式 fallback（基于太阳星座 / 日主的静态映射）。
2. LLM 文本返回但 JSON 解析失败 → 正则截取首个 JSON 块；仍失败则 fallback。
3. JSON 缺失字段 → 自动补默认值（`"unknown"` / `[]`），同时记录到 `incomplete_fields`。

缓存：对输入 `raw_symbols` 进行稳定哈希（仅限已提供键）作为 key；默认仅缓存“非 fallback”结果，避免降级缓存污染；可通过 `use_cache=False` 禁用。

指标 (metrics): 使用 `bersona.structuring.metrics.snapshot()` 获取：
```jsonc
{
    "pipeline": {"calls": 3, "success": 3, "fallback": 1, ...},
    "cache": {"size": 2, "hits": 5, "misses": 1, ...},
    "llm": {"total_calls": 3, "models": {"stub-1": {"calls": 3}}},
    "timestamp": 1730xxxx.xxx
}
```

测试策略：通过 monkeypatch stub LLM 保证 deterministic；真实外部 API 冒烟测试可在 CI 中跳过（未来扩展）。

未来扩展（规划中）：批量结构化接口、向量化投影、可配置多模型 fallback 链、本地轻量模型、输入脱敏 (`redact_inputs`)、行星相位聚合特征。

### 批量接口 (Experimental)

`structure_features_batch(list_of_raw_symbols, *, parallel=True, dedupe=True, model="stub-1") -> List[StructuredPersonaFeatures]`

特性：
1. 去重：`dedupe=True` 时相同符号集合仅计算一次（仍保持输出顺序）。
2. 可选并行：`parallel=True` 使用线程池（I/O bound LLM 调用友好）。
3. 失败隔离：单条异常自动 fallback，不影响其它条目。
4. 复用缓存：内部仍使用单条 API 的缓存与指标统计。

示例：
```python
from bersona.structuring.engine import structure_features_batch

batch = [
    {"astrology_raw": {"sun_sign": "Virgo"}},
    {"astrology_raw": {"sun_sign": "Virgo"}},  # duplicate
    {"astrology_raw": {"sun_sign": "Aries"}},
]
personae = structure_features_batch(batch, parallel=True)
for p in personae:
        print(p.core_identity, p.fallback)
```

当前状态：实验性（P2），接口可能随后续批量 Prompt 优化而调整。

## 🗺️ 路线图

项目路线图现已聚焦：占星基础 → 高保真本命盘 → 占星画像生态。欢迎查看并参与讨论。

🔭 **[查看项目路线图 (ROADMAP.md)](./ROADMAP.md)**

## 项目结构
```
bersona/
├── .github/                  # GitHub 相关配置
│   ├── workflows/            # CI/CD 自动化工作流 (如：自动测试)
│   │   └── main.yml
│   └── ISSUE_TEMPLATE/       # 问题模板
│       ├── bug_report.md
│       └── feature_request.md
│
├── docs/                     # 项目文档 (未来使用 Sphinx 或 MkDocs)
│   └── index.md
│
├── examples/                 # 使用示例代码
│   └── simple_run.py
│
├── src/
│   └── bersona/                # Bersona 库的源代码根目录
│       ├── __init__.py         # 包的入口，定义公共 API
│       ├── client.py           # Bersona 主客户端类
│       │
│       ├── kernels/            # 【计算引擎】占星内核模块
│       │   ├── __init__.py
│       │   ├── base.py         # 内核抽象基类
│       │   └── astrology_kernel.py # 占星计算内核（太阳/月亮/上升/行星/宫位）
│       │
│       ├── structuring/        # 【特征结构化】模块
│       │   ├── __init__.py
│       │   ├── schemas.py      # 结构化数据模型
│       │   ├── astrology_structurer.py # 占星数据结构化逻辑
│       │
│       ├── llm/                # 【LLM 交互】模块
│       │   ├── __init__.py
│       │   ├── prompts.py      # 存储所有的 Prompt 模板
│       │   └── clients.py      # 封装对不同 LLM API 的调用
│       │
│       ├── utils/              # 通用工具函数
│       │   ├── __init__.py
│       │   └── time_utils.py   # 例如：日期和时区处理
│       │
│       └── exceptions.py       # 自定义异常类
│
├── tests/                    # 测试代码
│   ├── __init__.py
│   ├── test_client.py
│   ├── kernels/
│   │   ├── test_astrology_kernel.py
│   └── structuring/
│       └── test_structurers.py
│
├── .env.example              # 环境变量模板文件
├── .gitignore                # Git 忽略文件配置
├── CODE_OF_CONDUCT.md        # 行为准则
├── CONTRIBUTING.md           # 贡献指南
├── LICENSE                   # 项目许可证
├── README.md                 # 项目介绍
└── pyproject.toml            # [核心] 项目元数据、依赖项和构建配置
```

## 🙌 如何贡献

Bersona 是一个开源项目，我们欢迎各种形式的贡献！当前战略聚焦于占星体系的深度迭代；如果你对行星相位、宫位解释标准化、Prompt 压缩或生成风格控制有想法，期待你的 Issue / PR。

请查阅我们的 `CONTRIBUTING.md` 文件，了解如何开始。

## ⚖️ 免责声明

本项目旨在提供基于占星符号学的娱乐、灵感与自我探索洞察。所有输出不应视为决定性预测或替代专业心理、医疗、法律或财务建议。请保持批判性与开放心态使用。

## 🔄 焦点迁移说明 (Focus Migration)

白皮书 V1.0 与早期 README 曾包含八字等多体系示例。2025-10 起我们选择“纵向深耕占星”战略：
1. 避免多体系术语冲突与 Schema 早期膨胀。
2. 将资源集中于行星/宫位/相位语义质量与 Prompt 稳定性。
3. 提高缓存命中与测试覆盖一致性（单一符号域）。

已移除早期多体系（八字）相关代码；后续是否重新引入将依据社区 RFC 评估。

## 📄 许可证

本项目基于 MIT 许可证。详情请参阅 `LICENSE` 文件。