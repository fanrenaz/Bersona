# Bersona 🧬 生成式用户画像引擎

**只需一个生日，即可解决用户冷启动问题，生成丰富、高维度的用户画像。**

[![PyPI version](https://badge.fury.io/py/bersona.svg)](https://badge.fury.io/py/bersona)
[![许可证: MIT](https://img.shields.io/badge/许可证-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Discord](https://img.shields.io/discord/YOUR_DISCORD_ID?label=加入我们&logo=discord)](https://discord.gg/YOUR_INVITE_LINK)

---

个性化系统虽然强大，但在面对新用户时，总会因**冷启动问题**而失效。在缺乏行为数据的情况下，推荐内容只能流于通用，导致用户流失率高。

**Bersona** 正是为解决这一难题而生。它利用用户的一个通用信息——**出生日期**——即时生成富有洞察力的高维度用户画像。我们将占星学、八字等古老体系不视为算命，而是看作经过时间考验的复杂人格分析框架。Bersona 将这些框架解码为结构化数据，并利用大型语言模型（LLM）生成远比随机猜测更精准、更深刻的用户画像。

## ✨ 核心特性

*   ⚡️ **即时冷启动解决方案**：仅需一个生日，即可生成详尽的用户画像，无需任何用户行为数据。
*   📈 **渐进式增强**：从一个日期开始，便可获得基础画像；用户还可选择性提供出生时间和地点，以解锁更高保真度的画像。
*   🧩 **模块化与高扩展性**：采用可插拔的“内核”设计。从占星学和八字开始，未来可轻松扩展至更多体系。
*   🤖 **模型无关**：兼容各类大型语言模型（OpenAI, Claude, Llama 等），你可以自由选择驱动引擎的大脑。
*   🔒 **隐私优先架构**：核心计算可在本地运行，用户的敏感出生信息无需发送到任何云端服务器。
*   💡 **不止是标签，更是洞察**：你得到的不再是简单的“天蝎座”，而是更具可操作性的洞察，例如：“该用户可能重视隐私和深度连接，偏好真实、拒绝肤浅的内容。”

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

    # 2. (可选) 提供完整信息，获取高保真画像
    # full_persona = b.get_persona(
    #     birth_date="1990-08-25",
    #     birth_time="14:30",
    #     latitude=34.0522,   # 纬度
    #     longitude=-118.2437 # 经度
    # )
    # print(full_persona)
    ```

## 🤔 工作原理

Bersona 的工作流基于一个简洁而强大的流水线，并支持“渐进式增强”。

`[用户输入] -> [计算引擎] -> [特征结构化] -> [LLM] -> [画像JSON]`

1.  **L1: 基础画像 (仅需日期)**：当仅提供 `birthDate` 时，Bersona 会计算太阳星座（占星学）和日主（八字）等核心要素。
2.  **L2: 高保真画像 (日期 + 时间 + 地点)**：当提供完整信息时，系统将解锁更丰富的数据集，包括上升星座、月亮星座、占星学宫位以及完整的八字命盘。

项目的魔法发生在**特征结构化层**，它将晦涩的原始数据（如 `太阳处女座`）翻译成对 LLM 友好的、有意义的标签（如 `{"core_identity": "注重细节、善于分析、有服务精神"}`）。

> **我们的理念**：我们不声称100%的准确性。我们将这些古老体系视为提供了一种强大的 **“强效先验”（Informative Prior）** 。它们提供了一个**优于随机的起点**，能够显著加速个性化系统对用户真实偏好的收敛过程。

## 🗺️ 路线图

我们为 Bersona 制定了详细的发展路线图，从基础的 MVP 到未来的生态系统建设。我们欢迎所有感兴趣的开发者和爱好者加入我们，共同塑造个性化技术的未来。

� **[查看详细的项目路线图 (ROADMAP.md)](./ROADMAP.md)**

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
│       ├── kernels/            # 【计算引擎】内核模块
│       │   ├── __init__.py
│       │   ├── base.py         # 定义所有内核的抽象基类
│       │   ├── astrology_kernel.py # 占星学计算内核
│       │   └── bazi_kernel.py    # 八字计算内核
│       │
│       ├── structuring/        # 【特征结构化】模块
│       │   ├── __init__.py
│       │   ├── schemas.py      # 定义结构化数据的 Pydantic 模型或 TypedDicts
│       │   ├── astrology_structurer.py # 占星数据结构化逻辑
│       │   └── bazi_structurer.py    # 八字数据结构化逻辑
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
│   │   └── test_bazi_kernel.py
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

Bersona 是一个开源项目，我们欢迎各种形式的贡献！无论你是开发者、数据科学家，还是占星/八字爱好者，我们都期待你的加入。

请查阅我们的 `CONTRIBUTING.md` 文件，了解如何开始。

## ⚖️ 免责声明

Bersona 项目旨在提供用于娱乐、灵感启发和自我探索的个性化洞察。其生成的所有内容不应被视为决定性的命运预测，也不能替代专业的心理、医疗或财务建议。我们鼓励用户以开放和批判性的思维来使用 Bersona。

## 📄 许可证

本项目基于 MIT 许可证。详情请参阅 `LICENSE` 文件。