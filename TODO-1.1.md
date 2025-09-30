# TODO- [x] **定义内核基类**: 在 `- [x] **依赖选型与安装**:
    - [x] 研究并选择一个可靠的 Python 库用于公历到农历（干支历）的转换。推荐选项：`sxtwl`。
    - [x] 将选定的库添加到 `pyproject.toml` 的 `[project.dependencies]` 中。
- [x] **创建文件**: 创建 `src/bersona/kernels/bazi_kernel.py`。
- [x] **实现 `BaziKernel` 类**:
    - [x] 类应继承自 `BaseKernel`。
    - [x] 实现 `calculate(self, birth_date: date) -> dict` 方法。
    - [x] 在方法内部，使用所选库将公历 `birth_date` 转换为对应的干支纪日。
    - [x] 提取日柱的天干作为“日主 (Day Master)”。
    - [x] 方法应返回一个字典，格式为 `{"day_master": "庚金"}` (建议使用中文名称以方便后续 Prompt 处理)。
- [x] **编写单元测试**: 在 `tests/kernels/test_bazi_kernel.py` 中为 `BaziKernel` 编写测试。
    - [x] 选取几个已知日主的公历日期作为测试用例。
    - [x] 验证 `calculate` 方法是否能返回正确的日主。例如，`1990-08-25` 的日主是“庚午”，所以天干是“庚”。ernels/base.py` 中创建 `BaseKernel` 抽象基类。
    - [x] 定义一个抽象方法 `calculate(self, **kwargs) -> dict`，所有内核都必须实现此方法。
    - [x] 在 `src/bersona/kernels/__init__.py` 中导出 `BaseKernel`。st: 核心计算内核 (MVP)

本任务清单详细拆解了 **Bersona 基础版 (MVP)** 路线图中的第一个关键成果：**核心计算内核**。

## 1. 内核基础架构

-   [ ] **定义内核基类**: 在 `src/bersona/kernels/base.py` 中创建 `BaseKernel` 抽象基类。
    -   [ ] 定义一个抽象方法 `calculate(self, **kwargs) -> dict`，所有内核都必须实现此方法。
    -   [ ] 在 `src/bersona/kernels/__init__.py` 中导出 `BaseKernel`。

## 2. 占星学内核 (`astrology_kernel`)

- [x] **创建文件**: 创建 `src/bersona/kernels/astrology_kernel.py`。
- [x] **实现 `AstrologyKernel` 类**:
    - [x] 类应继承自 `BaseKernel`。
    - [x] 实现 `calculate(self, birth_date: date) -> dict` 方法。
    - [x] 在方法内部，根据输入的 `birth_date` (月和日) 计算太阳星座。
    - [x] 方法应返回一个字典，格式为 `{"sun_sign": "Virgo"}`。
- [x] **编写单元测试**: 在 `tests/kernels/test_astrology_kernel.py` 中为 `AstrologyKernel` 编写测试。
    - [x] 测试所有 12 个星座的典型日期。
    - [x] 测试每个星座的边界日期（例如，3月20日和21日，以验证白羊座和双鱼座的划分）。
    - [x] 测试闰年日期。

## 3. 八字内核 (`bazi_kernel`)

-   [ ] **依赖选型与安装**:
    -   [ ] 研究并选择一个可靠的 Python 库用于公历到农历（干支历）的转换。推荐选项：`sxtwl`。
    -   [ ] 将选定的库添加到 `pyproject.toml` 的 `[project.dependencies]` 中。
-   [ ] **创建文件**: 创建 `src/bersona/kernels/bazi_kernel.py`。
-   [ ] **实现 `BaziKernel` 类**:
    -   [ ] 类应继承自 `BaseKernel`。
    -   [ ] 实现 `calculate(self, birth_date: date) -> dict` 方法。
    -   [ ] 在方法内部，使用所选库将公历 `birth_date` 转换为对应的干支纪日。
    -   [ ] 提取日柱的天干作为“日主 (Day Master)”。
    -   [ ] 方法应返回一个字典，格式为 `{"day_master": "庚金"}` (建议使用中文名称以方便后续 Prompt 处理)。
-   [ ] **编写单元测试**: 在 `tests/kernels/test_bazi_kernel.py` 中为 `BaziKernel` 编写测试。
    -   [ ] 选取几个已知日主的公历日期作为测试用例。
    -   [ ] 验证 `calculate` 方法是否能返回正确的日主。例如，`1990-08-25` 的日主是“庚午”，所以天干是“庚”。