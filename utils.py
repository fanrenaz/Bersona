"""占星计算与辅助工具函数

新增:
    - parse_birth_datetime: 支持多种输入格式统一为 timezone-aware datetime
    - get_city_coordinates: 根据中国城市名称(中英文/拼音)返回经纬度
"""
from typing import Optional, Union, Dict
from datetime import datetime, timezone, timedelta
import re
import json
import os
from .constants import ZODIAC_SIGNS

__all__ = [
    "angle_to_sign", "normalize_angle", "angular_distance",
    "parse_birth_datetime", "get_city_coordinates",
    "parse_admin_location", "geocode_china_location"
]
__all__.append("chart_to_text")

def normalize_angle(angle: float) -> float:
    """归一化角度到 0-360"""
    return angle % 360


def angle_to_sign(angle: float) -> str:
    a = normalize_angle(angle)
    for name, start in ZODIAC_SIGNS:
        if start <= a < start + 30:
            return name
    return "Aries"  # 理论上不会到这里


def angular_distance(a1: float, a2: float) -> float:
    """返回两个角度的最小分离 (0-180)"""
    diff = abs(normalize_angle(a2) - normalize_angle(a1)) % 360
    return diff if diff <= 180 else 360 - diff

# ---------------- ChartResult 转文本 ----------------

def chart_to_text(chart) -> str:
    """将 ChartResult 全量结构序列化为可嵌入 LLM 提示的纯文本。

    输出包含:
      - Ascendant
      - Houses (编号 + 黄经 + 星座)
      - Planets (名称 + 黄道经纬度 + 星座 + 逆行)
      - Aspects (行星1-行星2 相位 分离差值 容许度)
      - Mutual Receptions
    """
    lines = []
    lines.append(f"Ascendant: sign={chart.ascendant.sign} longitude={chart.ascendant.longitude:.2f}")
    lines.append("Houses:")
    for h in chart.houses:
        lines.append(f"  House {h.house}: {h.cusp_longitude:.2f}° {h.cusp_sign}")
    lines.append("Planets:")
    for name, p in chart.planets.items():
        lines.append(f"  {name}: lon={p.ecliptic_longitude:.2f}° lat={p.ecliptic_latitude:.2f}° sign={p.sign} retrograde={p.retrograde}")
    lines.append("Aspects:")
    for a in chart.aspects:
        lines.append(f"  {a.planet1}-{a.planet2} {a.aspect} sep={a.separation:.2f} diff={a.difference:.2f} orb={a.orb_allowed:.2f}")
    lines.append("MutualReceptions:")
    for m in chart.mutual_receptions:
        lines.append(f"  {m.planet1}<->{m.planet2} signs={m.signs[0]}/{m.signs[1]} scheme={m.scheme}")
    return "\n".join(lines)

# ---------------- 时间解析工具 ----------------

ISO_PATTERNS = [
    # 2025-10-12T14:30:00+08:00 / 2025-10-12 14:30:00 / 2025/10/12 14:30
    r"^(\d{4}-\d{2}-\d{2})[T\s](\d{2}:\d{2}:\d{2})([+-]\d{2}:?\d{2})?$",
    r"^(\d{4}-\d{2}-\d{2})[T\s](\d{2}:\d{2})([+-]\d{2}:?\d{2})?$",
    r"^(\d{4}/\d{2}/\d{2})[\s](\d{2}:\d{2})([+-]\d{2}:?\d{2})?$",
]

CHINESE_DATE_PATTERN = r"^(\d{4})年(\d{1,2})月(\d{1,2})日\s?(\d{1,2})时?(\d{1,2})?分?(\d{1,2})?秒?(?:\s*([+-]\d{2}:?\d{2}))?$"

def _parse_offset(tz_str: Optional[str]) -> timezone:
    if not tz_str:
        # 默认使用 +08:00 (中国标准时间) 可按需改成 UTC
        return timezone.utc if False else timezone(timedelta(hours=8))
    # 形如 +0800 / +08:00 / -0530
    m = re.match(r"([+-])(\d{2}):?(\d{2})", tz_str)
    if not m:
        return timezone.utc
    sign = 1 if m.group(1) == '+' else -1
    hh = int(m.group(2))
    mm = int(m.group(3))
    return timezone(timedelta(hours=sign*hh, minutes=sign*mm))

def parse_birth_datetime(value: Union[str, int, float, datetime]) -> datetime:
    """将多种输入格式转换为 timezone-aware datetime。

    支持:
      - 已有 timezone-aware datetime: 直接返回
      - naive datetime: 自动补上默认时区 (+08:00)
      - ISO 字符串: 2025-10-12T14:30:00+08:00 / 2025-10-12 14:30:00
      - 简化字符串: 2025/10/12 14:30
      - 中文格式: 2025年10月12日14时30分 (可含秒与偏移)
      - Unix 时间戳 (int/float): 视为秒，默认转换为 UTC 再转 +08:00
    """
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone(timedelta(hours=8)))
    if isinstance(value, (int, float)):
        dt_utc = datetime.fromtimestamp(value, tz=timezone.utc)
        return dt_utc.astimezone(timezone(timedelta(hours=8)))
    if not isinstance(value, str):
        raise TypeError("不支持的日期输入类型")

    s = value.strip()
    # ISO / 常见格式
    for pat in ISO_PATTERNS:
        m = re.match(pat, s)
        if m:
            date_part = m.group(1).replace('/', '-')
            time_part = m.group(2)
            tz_part = m.group(3)
            if ':' not in time_part:
                raise ValueError('时间格式不符合预期')
            # 若无秒补 00
            if len(time_part.split(':')) == 2:
                time_part += ':00'
            tzinfo = _parse_offset(tz_part)
            dt = datetime.fromisoformat(f"{date_part} {time_part}")
            return dt.replace(tzinfo=tzinfo)

    # 中文格式
    m = re.match(CHINESE_DATE_PATTERN, s)
    if m:
        year, month, day = int(m.group(1)), int(m.group(2)), int(m.group(3))
        hour = int(m.group(4)) if m.group(4) else 0
        minute = int(m.group(5)) if m.group(5) else 0
        second = int(m.group(6)) if m.group(6) else 0
        tz_part = m.group(7)
        tzinfo = _parse_offset(tz_part)
        return datetime(year, month, day, hour, minute, second, tzinfo=tzinfo)

    # 直接尝试 python fromisoformat (可能包含时区)
    try:
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone(timedelta(hours=8)))
        return dt
    except Exception:
        pass

    raise ValueError(f"无法解析日期字符串: {value}")

# ---------------- 城市坐标工具 ----------------


_GEOCODER = None
_GEOCODE_CACHE: Dict[str, tuple] = {}
# ---------------- 行政区规范解析与地理编码 ----------------

PROVINCE_KEYWORDS = [
    '北京市','天津市','上海市','重庆市',
    '河北省','山西省','辽宁省','吉林省','黑龙江省','江苏省','浙江省','安徽省','福建省','江西省','山东省','河南省','湖北省','湖南省','广东省','海南省',
    '四川省','贵州省','云南省','陕西省','甘肃省','青海省','台湾省',
    '内蒙古自治区','广西壮族自治区','西藏自治区','宁夏回族自治区','新疆维吾尔自治区','香港特别行政区','澳门特别行政区'
]

def parse_admin_location(s: str) -> Dict[str,str]:
    """解析输入格式: 省/自治区/直辖市 + 市/州。

    期望格式示例:
      - 浙江省杭州市
      - 北京市 (直辖市可只写一个)
      - 内蒙古自治区呼和浩特市
    返回: {'province':..., 'city':...}
    若无法解析抛出 ValueError。
    """
    if not s:
        raise ValueError('空的地点输入')
    s = s.strip()
    # 尝试匹配已知省/自治区关键字前缀
    for prov in sorted(PROVINCE_KEYWORDS, key=len, reverse=True):
        if s.startswith(prov):
            rest = s[len(prov):]
            if prov.endswith('市') and not rest:  # 直辖市无需 city 再次指定
                return {'province': prov, 'city': prov[:-1]}  # 去掉 “市” 作为城市名
            # 常见市/州/地区后缀
            m = re.match(r'(.+?)(市|州|地区|盟)$', rest)
            if m:
                city = m.group(1)
                return {'province': prov, 'city': city}
            raise ValueError(f'未识别城市部分: {rest}')
    # 若是仅一个直辖市名称（如 北京市）
    m2 = re.match(r'^(北京|天津|上海|重庆)市$', s)
    if m2:
        city_base = m2.group(1)
        return {'province': f'{city_base}市', 'city': city_base}
    raise ValueError(f'无法解析行政区地点: {s}')

def _ensure_geocoder():
    global _GEOCODER
    if _GEOCODER is None:
        try:
            from geopy.geocoders import Nominatim
            _GEOCODER = Nominatim(user_agent='bersona_geocoder')
        except Exception as e:
            _GEOCODER = False  # 标记不可用

def geocode_china_location(admin_str: str) -> Optional[tuple]:
    """地理编码中国地点（省市格式）。使用 OpenStreetMap Nominatim。

    参数: admin_str 如 '浙江省杭州市'
    返回: (lat, lon) 或 None
    说明: 在线请求，有速率限制；结果缓存以减少重复查询。
    """
    parsed = parse_admin_location(admin_str)
    key = parsed['province'] + parsed['city']
    if key in _GEOCODE_CACHE:
        return _GEOCODE_CACHE[key]
    _ensure_geocoder()
    if not _GEOCODER:
        return None
    query = f"{parsed['city']},{parsed['province']},China"
    try:
        loc = _GEOCODER.geocode(query)
        if loc:
            coord = (loc.latitude, loc.longitude)
            _GEOCODE_CACHE[key] = coord
            return coord
    except Exception:
        return None
    return None
