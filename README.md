# Bersona 星盘生成 (src 布局)

一个使用 Skyfield (以及可选 Swiss Ephemeris) 生成西方占星出生星盘并可调用 LLM 生成解释的 Python 包。现采用标准 `src/` 布局与 Pydantic 2 模型。安装后可直接 `from bersona import Bersona`。

## 目录结构
```
pyproject.toml
requirements.txt (开发用，可选)
src/
  bersona/
    __init__.py
    _version.py
    astrology_kernel.py
    constants.py
    models.py
    prompts.py
    utils.py
tests/
  test_chart_basic.py
  test_version.py
.github/
  workflows/ci.yml
scripts/
  bump_version.py
```

## 版本号管理
当前版本通过 `src/bersona/_version.py` 与 `pyproject.toml` 同步维护，公开 `bersona.__version__`。

查看版本：
```python
import bersona
print(bersona.__version__)
```

使用脚本自动 bump：
```bash
python scripts/bump_version.py patch   # 0.1.0 -> 0.1.1
python scripts/bump_version.py minor   # 0.1.x -> 0.2.0
python scripts/bump_version.py major   # 0.x.y -> 1.0.0
```
脚本会同时修改 `pyproject.toml` 与 `_version.py`，请提交并打 tag：
```bash
git add pyproject.toml src/bersona/_version.py
git commit -m "chore: bump version"
git tag v$(python -c "import bersona;print(bersona.__version__)")
```

## CI (GitHub Actions)
工作流文件位于 `.github/workflows/ci.yml`，在 push / PR 到 `main` 时执行：
- 多 Python 版本 (3.10 / 3.11 / 3.12)
- 安装核心与可选依赖 (`.[all]`)
- 缓存 pip 与 Skyfield 星历目录
- 运行 pytest
- 构建 wheel 包

后续可扩展：
- 增加 Ruff/Black 格式检查
- 发布时自动上传到 PyPI（在 tag 触发下添加发布作业）
- 增量测试报告 & 覆盖率上传 Codecov

## 安装
推荐使用 `pip` 基于 `pyproject.toml` 安装：
```bash
pip install .            # 本地开发安装
# 或构建轮子
pip wheel . -w dist
```
仅核心功能（行星 + 模型）：
```bash
pip install .
```
带 Placidus、LLM、地理编码全部可选依赖：
```bash
pip install .[all]
```
按需安装：
```bash
pip install .[placidus]
pip install .[llm]
pip install .[geocode]
```

若只想快速体验（使用旧的 requirements 方式）：
```bash
pip install -r requirements.txt
```

## 快速开始
```python
from bersona import Bersona
import zoneinfo
from datetime import datetime

b = Bersona()
tz = zoneinfo.ZoneInfo('Asia/Shanghai')
dt = datetime(1990, 5, 17, 14, 30, tzinfo=tz)
chart = b.generate_chart(dt, latitude=31.2304, longitude=121.4737, house_system='placidus')
print(chart.summary())
```

## 自定义系统提示 (LLM)
`astrology_describe` 现支持传入 `system_prompt` 覆盖默认语言模板：
```python
if b.llm_available:
    desc = b.astrology_describe(chart, language='zh', system_prompt='你是一位温暖且专业的占星导师，请分段解释：')
    print(desc.text)
```

## 主要特性
- 行星位置：Sun..Pluto 黄道经纬度 (Skyfield)
- 上升与宫位：等宫 / Placidus (需 pyswisseph)
- 主要相位与可自定义 orb
- 互溶接纳 (Mutual Reception) 传统/现代主宰方案
- 多格式出生时间解析（含中文日期）
- 城市行政区解析 + 可选在线地理编码
- LLM 集成生成占星文字解释 (OpenAI 兼容)

## 环境变量
- `BERSONA_EPHEMERIS` 指定星历文件 (默认 de421.bsp)
- `SKYFIELD_CACHE_DIR` 自定义 Skyfield 缓存目录
- `OPENAI_API_KEY` / `OPENAI_KEY` LLM 密钥
- `OPENAI_BASE_URL` 自定义 API 端点
- `OPENAI_MODEL` 默认模型名称

## 测试
```bash
pytest -q
```

## 构建与分发建议
发布前:
1. 使用 bump 脚本或手动更新版本号
2. 生成分发包：`python -m build`
3. 上传：`twine upload dist/*`

### 发布到 TestPyPI (推荐先试)
```bash
python -m pip install --upgrade build twine
python -m build  # 生成 dist/*.whl 与 *.tar.gz
twine upload --repository-url https://test.pypi.org/legacy/ dist/*

# 验证安装（使用隔离虚拟环境）
python -m venv .venv-test
source .venv-test/bin/activate
pip install --index-url https://test.pypi.org/simple --extra-index-url https://pypi.org/simple bersona
python -c "import bersona;print(bersona.__version__)"
```

### 正式发布到 PyPI
准备：在 GitHub 仓库 Settings -> Secrets 添加 `PYPI_API_TOKEN`（pypi.org 上创建的 token）。

两种方式：
1. 手动：
  ```bash
  python -m build
  twine upload dist/*
  ```
2. 自动 (推荐)：
  - 先 bump 版本并提交：
    ```bash
    python scripts/bump_version.py patch
    git add pyproject.toml src/bersona/_version.py
    git commit -m "chore: release v$(python -c 'import bersona;print(bersona.__version__)')"
    git tag v$(python -c 'import bersona;print(bersona.__version__)')
    git push --tags
    ```
  - 触发 `release.yml` 工作流自动构建并上传。

### 版本与 Tag 约定
- 使用语义化版本：`MAJOR.MINOR.PATCH`
- 预发布可采用：`0.2.0a1`, `0.2.0rc1`（当前 bump 脚本未自动生成，需手动改版本号）。
- Tag 格式：`vX.Y.Z` 与 `pyproject.toml` / `_version.py` 对应。

### 常见发布问题
- 403 Forbidden：检查 `PYPI_API_TOKEN` 是否具有项目上传权限。
- 文件已存在：可能重复上传同版本；删除 dist/ 重建并 bump 新版本号。
- 依赖未正确安装：确认 `pyproject.toml` 中 `dependencies` 与 extras 正确，避免只写在旧的 `requirements.txt`。
- 缺少 License：PyPI 会显示 “No license” 警告；已添加 `LICENSE` 文件即可。

## 后续改进 (Roadmap)
- Transit / Progressions 支持
- 更多天体与相位类型
- 容许度细化按行星分类
- LLM 结构化输出 (JSON schema)
- chart_snapshot 填充关键信息摘要
- 自动发布工作流 (tag push -> PyPI)

## License
建议添加 MIT 或 Apache-2.0 许可证，可在 `pyproject.toml` 与根目录添加 `LICENSE` 文件。

(README 已更新：新增版本管理与 CI 章节。)
