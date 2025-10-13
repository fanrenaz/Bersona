from datetime import datetime, timedelta, timezone
import re
from typing import Dict, Any, List, Optional
import os
import logging
# 初始化日志
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

from .constants import (
    ZODIAC_SIGNS,
    TRADITIONAL_RULERS,
    MODERN_RULERS,
    MAJOR_ASPECTS_DEFAULT_ORBS,
    ASPECT_DEGREES,
    PLANET_NAMES,
)
from .utils import angle_to_sign, angular_distance, parse_birth_datetime, chart_to_text
from .prompts import BASE_PROMPTS
from .models import (
    ChartInput,
    ChartSettings,
    ChartResult,
    Ascendant,
    HouseCusp,
    PlanetPosition,
    Aspect,
    MutualReception,
    AstrologyDesc,
)

try:
    from skyfield.api import load, wgs84
    _EPHEMERIS_NAME = os.getenv('BERSONA_EPHEMERIS', 'de421.bsp')
    cache_dir = os.getenv('SKYFIELD_CACHE_DIR')
    if cache_dir:
        os.makedirs(cache_dir, exist_ok=True)
        from skyfield.api import Loader
        loader = Loader(cache_dir)
        _TS = loader.timescale()
        ephemeris_path = os.path.join(cache_dir, _EPHEMERIS_NAME)
        if not os.path.exists(ephemeris_path):
            approx_size_mb = '20' if 'de421' in _EPHEMERIS_NAME else ('120' if 'de440' in _EPHEMERIS_NAME else '若干')
            logger.info(f"[Bersona] 尚未发现星历文件 '{_EPHEMERIS_NAME}'，首次使用将自动下载约 {approx_size_mb}MB，需保持网络畅通...")
        _EPHEMERIS = loader(_EPHEMERIS_NAME)
    else:
        _TS = load.timescale()
        home_cache = os.path.join(os.path.expanduser('~'), '.skyfield', _EPHEMERIS_NAME)
        if not os.path.exists(home_cache):
            approx_size_mb = '20' if 'de421' in _EPHEMERIS_NAME else ('120' if 'de440' in _EPHEMERIS_NAME else '若干')
            logger.info(f"[Bersona] 首次使用星历 '{_EPHEMERIS_NAME}'，将自动下载约 {approx_size_mb}MB，需保持网络畅通...")
        _EPHEMERIS = load(_EPHEMERIS_NAME)
    _PLANETS = {
        "Sun": _EPHEMERIS["sun"],
        "Moon": _EPHEMERIS["moon"],
        "Mercury": _EPHEMERIS["mercury"],
        "Venus": _EPHEMERIS["venus"],
        "Mars": _EPHEMERIS["mars"],
        "Jupiter": _EPHEMERIS["jupiter barycenter"],
        "Saturn": _EPHEMERIS["saturn barycenter"],
        "Uranus": _EPHEMERIS["uranus barycenter"],
        "Neptune": _EPHEMERIS["neptune barycenter"],
        "Pluto": _EPHEMERIS["pluto barycenter"],
    }
    _SKYFIELD_AVAILABLE = True
    logger.debug("Skyfield 已加载: %s", _EPHEMERIS_NAME)
except Exception as e:
    logger.warning("Skyfield 加载失败: %s", e)
    _SKYFIELD_AVAILABLE = False

try:
    import swisseph as swe
    _SWISSEPH_AVAILABLE = True
    logger.debug("SwissEph 已加载")
except Exception as e:
    logger.warning("SwissEph 加载失败: %s", e)
    _SWISSEPH_AVAILABLE = False

class Bersona:
    # 新增: 默认语言类属性（可按需扩展）
    DEFAULT_LANGUAGE = 'zh'

    def __init__(self,
                 llm_client: Any = None,
                 llm_model: Optional[str] = None,
                 system_prompt: Optional[str] = None) -> None:
        """
        可选参数:
        llm_client: 传入已构造好的 OpenAI 客户端(或兼容接口对象)，则不再内部自动创建
        llm_model: 指定使用的模型；若为空且使用环境变量模式，则读取 OPENAI_MODEL
        system_prompt: 覆盖默认的 system prompt
        """
        self.available_skyfield = _SKYFIELD_AVAILABLE
        self.available_swisseph = _SWISSEPH_AVAILABLE
        self._llm_client = None
        self._llm_model = None

        default_lang = os.getenv("BERSONA_DEFAULT_LANG", self.DEFAULT_LANGUAGE)
        # 若显式传入 system_prompt 则使用；否则按语言默认
        self.system_prompt: Optional[str] = system_prompt or BASE_PROMPTS.get(default_lang, BASE_PROMPTS[self.DEFAULT_LANGUAGE])

        logger.debug("初始化 Bersona: skyfield=%s swisseph=%s", self.available_skyfield, self.available_swisseph)

        if llm_client is not None:
            # 外部注入模式
            self._llm_client = llm_client
            self._llm_model = llm_model or os.getenv('OPENAI_MODEL')
            self.llm_available = True
            logger.info("使用外部注入的 LLM 客户端，模型=%s", self._llm_model)
        else:
            # 保留原环境变量自动创建逻辑
            api_key = None
            base_url = None
            try:
                api_key = os.getenv('OPENAI_API_KEY') or os.getenv('OPENAI_KEY')
                base_url = os.getenv('OPENAI_BASE_URL')
            except Exception as e:
                logger.debug("读取 OpenAI 环境变量失败: %s", e)
                api_key = None
            if api_key:
                try:
                    from openai import OpenAI
                    kwargs = {'api_key': api_key}
                    if base_url:
                        kwargs['base_url'] = base_url
                    self._llm_client = OpenAI(**kwargs)
                    self._llm_model = os.getenv('OPENAI_MODEL')
                    logger.info("LLM 客户端初始化成功，模型=%s", self._llm_model)
                except Exception as e:
                    logger.warning("LLM 初始化失败: %s", e)
                    self._llm_client = None
            self.llm_available = self._llm_client is not None

    # 新增: 设置 / 覆盖实例级 system prompt 的便捷方法
    def set_system_prompt(self, prompt: str) -> None:
        """
        设置实例级的 system prompt。传入空字符串将视为清除，自行回退到 BASE_PROMPTS 逻辑。
        """
        self.system_prompt = prompt or None

    def set_llm_client(self, client: Any, model: Optional[str] = None) -> None:
        """
        动态注入 / 替换 LLM 客户端。
        client: 需提供 chat.completions.create 接口的对象
        model: 若指定则更新模型；否则保留原值或再从环境变量读取
        """
        self._llm_client = client
        if model:
            self._llm_model = model
        elif not self._llm_model:
            self._llm_model = os.getenv('OPENAI_MODEL')
        self.llm_available = self._llm_client is not None
        logger.info("已更新 LLM 客户端，当前模型=%s", self._llm_model)

    def llm_chat(self, messages: List[Dict[str, str]], model: Optional[str] = None) -> Optional[str]:
        if not self.llm_available:
            logger.warning("LLM 不可用，跳过 llm_chat 调用")
            return None
        use_model = model or self._llm_model
        if not use_model:
            logger.error("未指定模型且环境变量 OPENAI_MODEL 未设置")
            raise ValueError('未指定模型名称，且环境变量 OPENAI_MODEL 未设置')
        logger.debug("调用 LLM: model=%s", use_model)
        try:
            resp = self._llm_client.chat.completions.create(
                model=use_model,
                messages=messages
            )
            if resp and resp.choices:
                content = resp.choices[0].message.content
                logger.debug("LLM 返回长度=%d", len(content or ""))
                return content
            logger.warning("LLM 无 choices 返回")
        except Exception as e:
            logger.error("LLM 调用异常: %s", e)
            return None
        return None

    def astrology_describe(self,
                           chart: ChartResult,
                           model: Optional[str] = None,
                           language: str = 'zh',
                           system_prompt: Optional[str] = None) -> AstrologyDesc:
        """调用 LLM 生成占星描述，并兼容多种包裹格式提取描述正文。
        支持多种输出标记。
        优先级：显式参数 system_prompt > 实例属性 self.system_prompt > 语言默认 BASE_PROMPTS。
        """
        if not self.llm_available:
            raise RuntimeError('LLM 不可用：请设置 OPENAI_API_KEY 并确保网络可访问。')

        # 修改: 使用实例属性 system_prompt
        if system_prompt:
            base_prompt = system_prompt
        elif self.system_prompt:
            base_prompt = self.system_prompt
        else:
            base_prompt = BASE_PROMPTS.get(language.split('-')[0], BASE_PROMPTS['en'])

        chart_text = chart_to_text(chart)
        messages = [
            {'role': 'system', 'content': base_prompt},
            {'role': 'user', 'content': chart_text},
        ]
        response = self.llm_chat(messages, model=model)
        if not response:
            raise RuntimeError('LLM 调用失败或返回空响应。')

        raw = response.strip()
        desc_extracted: str = raw

        # 尝试模式 1 / 2：宽松匹配带反引号的开始与结束
        patterns = [
            # 代码块语言标记，开始与结束均为独立代码块语言
            re.compile(r"```ASTROLOGY_DESC_START\s*\n(.*?)\n```ASTROLOGY_DESC_END", re.DOTALL),
            # 紧贴三反引号的单行写法
            re.compile(r"```ASTROLOGY_DESC_START```(.*?)```ASTROLOGY_DESC_END```", re.DOTALL),
            # 开始为语言标记，结束为普通反引号 (部分模型可能只给结束的 ``` )
            re.compile(r"```ASTROLOGY_DESC_START\s*\n(.*?)\n```", re.DOTALL),
            # 无反引号纯文本标记
            re.compile(r"ASTROLOGY_DESC_START(.*?)ASTROLOGY_DESC_END", re.DOTALL),
        ]
        for idx, pat in enumerate(patterns, start=1):
            m = pat.search(raw)
            if m:
                desc_extracted = m.group(1).strip()
                logger.debug("占星描述匹配成功: pattern=%d 长度=%d", idx, len(desc_extracted))
                break
        else:
            logger.warning("未匹配到任何 ASTROLOGY_DESC 标记模式，使用完整响应正文")

        # 去除可能残留的首尾反引号块
        if desc_extracted.startswith("```") and desc_extracted.endswith("```"):
            desc_extracted = desc_extracted[3:-3].strip()

        # 构建一个轻量快照（避免巨大 JSON）
        try:
            chart_snapshot = {
                'ascendant': chart.ascendant.sign if chart.ascendant else None,
                'planets': {k: v.sign for k, v in chart.planets.items()},
                'aspects_count': len(chart.aspects),
            }
        except Exception:
            chart_snapshot = {}

        return AstrologyDesc(
            text=desc_extracted,
            model_used=model or self._llm_model,
            language=language,
            chart_snapshot=chart_snapshot,
        )

    def generate_chart(self,
                       birth_dt_input: Any,
                       latitude: float = 39.9042,
                       longitude: float = 116.4074,
                       house_system: str = 'placidus',
                       aspect_orbs: Optional[Dict[str, float]] = None,
                       rulers_scheme: str = 'traditional') -> ChartResult:
        logger.info("开始生成星盘: raw_input=%s lat=%.4f lon=%.4f house_system=%s rulers_scheme=%s",
                    birth_dt_input, latitude, longitude, house_system, rulers_scheme)
        raw_input = birth_dt_input
        date_only_flag = False
        if isinstance(raw_input, str):
            date_only_patterns = [
                r"^\d{4}-\d{2}-\d{2}$",
                r"^\d{4}/\d{2}/\d{2}$",
                r"^\d{4}年\d{1,2}月\d{1,2}日$",
            ]
            for pat in date_only_patterns:
                if re.match(pat, raw_input.strip()):
                    date_only_flag = True
                    if '年' in raw_input:
                        m = re.match(r"^(\d{4})年(\d{1,2})月(\d{1,2})日$", raw_input.strip())
                        y, mo, d = m.groups()
                        raw_input = f"{y}-{int(mo):02d}-{int(d):02d} 12:00:00"
                    elif '/' in raw_input:
                        parts = raw_input.strip().split('/')
                        raw_input = f"{parts[0]}-{parts[1]}-{parts[2]} 12:00:00"
                    else:
                        raw_input = raw_input.strip() + ' 12:00:00'
                    break
        birth_dt = parse_birth_datetime(raw_input)
        logger.debug("解析时间结果: %s (tz=%s)", birth_dt, birth_dt.tzinfo)
        if birth_dt.tzinfo is None:
            raise ValueError("birth_dt 必须为带时区的 datetime")
        if house_system not in ('equal', 'placidus'):
            raise ValueError("house_system 仅支持 'equal'|'placidus'")
        if rulers_scheme not in ('traditional', 'modern'):
            raise ValueError("rulers_scheme 仅支持 'traditional'|'modern'")

        aspect_orbs = aspect_orbs or MAJOR_ASPECTS_DEFAULT_ORBS
        rulers_map = TRADITIONAL_RULERS if rulers_scheme == 'traditional' else MODERN_RULERS

        input_model = ChartInput(
            birth_datetime=birth_dt,
            latitude=latitude,
            longitude=longitude,
            house_system=house_system,
            rulers_scheme=rulers_scheme,
            aspect_orbs=aspect_orbs,
            date_only=date_only_flag,
        )
        settings_model = ChartSettings(
            house_system=house_system,
            rulers_scheme=rulers_scheme,
            aspect_orbs=aspect_orbs,
            libraries={'skyfield': self.available_skyfield, 'pyswisseph': self.available_swisseph},
        )

        ascendant_model: Optional[Ascendant] = None
        houses_list: List[HouseCusp] = []
        planets_dict: Dict[str, PlanetPosition] = {}
        aspects_list: List[Aspect] = []
        mutual_receptions_list: List[MutualReception] = []

        if self.available_skyfield:
            t = _TS.from_datetime(birth_dt)
        else:
            t = None

        ascendant_model = None
        if not date_only_flag:
            logger.debug("计算宫位: system=%s swisseph=%s", house_system, self.available_swisseph)
            asc_long: float
            if house_system == 'placidus' and self.available_swisseph:
                dt_utc = birth_dt.astimezone(timezone.utc)
                ut_hour = dt_utc.hour + dt_utc.minute / 60 + dt_utc.second / 3600
                jd_ut = swe.julday(dt_utc.year, dt_utc.month, dt_utc.day, ut_hour, swe.GREG_CAL)
                try:
                    cusps, ascmc = swe.houses(jd_ut, latitude, longitude, b'P')
                    asc_long = float(ascmc[0]) % 360
                    for i in range(1, 13):
                        cusp = float(cusps[i]) % 360
                        houses_list.append(HouseCusp(house=i, cusp_longitude=cusp, cusp_sign=angle_to_sign(cusp)))
                except Exception:
                    if not self.available_skyfield or t is None:
                        asc_long = None
                    else:
                        gast_hours = t.gast
                        asc_long = (gast_hours * 15 + longitude) % 360
                        for i in range(1, 13):
                            start = (asc_long + (i - 1) * 30) % 360
                            houses_list.append(HouseCusp(house=i, cusp_longitude=start, cusp_sign=angle_to_sign(start)))
            else:
                if not self.available_skyfield or t is None:
                    raise RuntimeError('缺少精确时间与 Skyfield，不计算等宫制宫位')
                gast_hours = t.gast
                lst_deg = (gast_hours * 15 + longitude) % 360
                asc_long = lst_deg
                for i in range(1, 13):
                    start = (asc_long + (i - 1) * 30) % 360
                    houses_list.append(HouseCusp(house=i, cusp_longitude=start, cusp_sign=angle_to_sign(start)))
            if 'asc_long' in locals() and asc_long is not None:
                ascendant_model = Ascendant(longitude=asc_long, sign=angle_to_sign(asc_long))
                logger.info("上升星座: %s %.2f°", ascendant_model.sign, ascendant_model.longitude)

        planet_longitudes: Dict[str, float] = {}
        if not self.available_skyfield:
            logger.error("Skyfield 不可用，无法计算行星位置")
            raise RuntimeError('Skyfield 不可用，无法计算行星位置。')
        if t is not None:
            earth = _EPHEMERIS['earth']
            prev_dt = birth_dt - timedelta(days=1)
            t_prev = _TS.from_datetime(prev_dt)
            for name, planet in _PLANETS.items():
                try:
                    astrometric = earth.at(t).observe(planet).apparent()
                    lat_ecl, lon_ecl, _ = astrometric.ecliptic_latlon()
                    lon_deg = float(lon_ecl.degrees) % 360
                    lat_deg = float(lat_ecl.degrees)
                    astrometric_prev = earth.at(t_prev).observe(planet).apparent()
                    lat_prev, lon_prev, _ = astrometric_prev.ecliptic_latlon()
                    lon_prev_deg = float(lon_prev.degrees) % 360
                    diff_raw = lon_deg - lon_prev_deg
                    if diff_raw < -180:
                        diff_raw += 360
                    elif diff_raw > 180:
                        diff_raw -= 360
                    retrograde = diff_raw < 0
                    planet_longitudes[name] = lon_deg
                    planets_dict[name] = PlanetPosition(
                        name=name,
                        ecliptic_longitude=lon_deg,
                        ecliptic_latitude=lat_deg,
                        sign=angle_to_sign(lon_deg),
                        retrograde=retrograde,
                    )
                    logger.debug("行星位置: %s lon=%.4f lat=%.4f sign=%s R=%s",
                                 name, lon_deg, lat_deg, angle_to_sign(lon_deg), retrograde)
                except Exception as e:
                    logger.warning("行星计算失败 %s: %s", name, e)

        planet_names = list(planets_dict.keys())
        for i in range(len(planet_names)):
            for j in range(i + 1, len(planet_names)):
                p1 = planet_names[i]
                p2 = planet_names[j]
                lon1 = planet_longitudes[p1]
                lon2 = planet_longitudes[p2]
                separation = angular_distance(lon1, lon2)
                for aspect_name, aspect_deg in ASPECT_DEGREES.items():
                    orb_allowed = aspect_orbs.get(aspect_name, MAJOR_ASPECTS_DEFAULT_ORBS.get(aspect_name, 0))
                    diff = abs(separation - aspect_deg)
                    if diff <= orb_allowed:
                        aspects_list.append(Aspect(
                            planet1=p1,
                            planet2=p2,
                            aspect=aspect_name,
                            separation=separation,
                            difference=diff,
                            orb_allowed=orb_allowed,
                        ))
                        logger.debug("发现相位: %s-%s %s 分离=%.2f 差值=%.2f 允许容许=%.2f",
                                     p1, p2, aspect_name, separation, diff, orb_allowed)
        logger.info("相位数量: %d", len(aspects_list))

        for i in range(len(planet_names)):
            for j in range(i + 1, len(planet_names)):
                p1 = planet_names[i]
                p2 = planet_names[j]
                sign1 = planets_dict[p1].sign
                sign2 = planets_dict[p2].sign
                ruler1 = rulers_map.get(sign1)
                ruler2 = rulers_map.get(sign2)
                if ruler1 == p2 and ruler2 == p1 and p1 != p2:
                    mutual_receptions_list.append(MutualReception(
                        planet1=p1,
                        planet2=p2,
                        scheme=rulers_scheme,
                        signs=(sign1, sign2)
                    ))
                    logger.debug("发现互容: %s <-> %s (%s/%s)", p1, p2, sign1, sign2)
        logger.info("互容数量: %d", len(mutual_receptions_list))
        chart_result = ChartResult(
            input=input_model,
            settings=settings_model,
            ascendant=ascendant_model,
            houses=houses_list,
            planets=planets_dict,
            aspects=aspects_list,
            mutual_receptions=mutual_receptions_list,
        )
        logger.info("星盘生成完成")
        return chart_result

if __name__ == "__main__":
    import zoneinfo
    tz = zoneinfo.ZoneInfo("Asia/Shanghai")
    dt = datetime(1990, 5, 17, 14, 30, tzinfo=tz)
    b = Bersona()
    chart = b.generate_chart(dt, 31.2304, 121.4737)
    logger.info("示例星盘 JSON 输出")
    print(chart.model_dump_json(indent=2, ensure_ascii=False))
