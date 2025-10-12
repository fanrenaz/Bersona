# ...migrated content from root astrology_kernel.py...
from datetime import datetime, timedelta, timezone
import re
from typing import Dict, Any, List, Optional
import math

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
    import os
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
            print(f"[Bersona] 尚未发现星历文件 '{_EPHEMERIS_NAME}'，首次使用将自动下载约 {approx_size_mb}MB，需保持网络畅通...")
        _EPHEMERIS = loader(_EPHEMERIS_NAME)
    else:
        _TS = load.timescale()
        home_cache = os.path.join(os.path.expanduser('~'), '.skyfield', _EPHEMERIS_NAME)
        if not os.path.exists(home_cache):
            approx_size_mb = '20' if 'de421' in _EPHEMERIS_NAME else ('120' if 'de440' in _EPHEMERIS_NAME else '若干')
            print(f"[Bersona] 首次使用星历 '{_EPHEMERIS_NAME}'，将自动下载约 {approx_size_mb}MB，需保持网络畅通...")
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
except Exception:
    _SKYFIELD_AVAILABLE = False

try:
    import swisseph as swe
    _SWISSEPH_AVAILABLE = True
except Exception:
    _SWISSEPH_AVAILABLE = False

class Bersona:
    def __init__(self) -> None:
        self.available_skyfield = _SKYFIELD_AVAILABLE
        self.available_swisseph = _SWISSEPH_AVAILABLE
        self._llm_client = None
        self._llm_model = None
        api_key = None
        base_url = None
        try:
            import os
            api_key = os.getenv('OPENAI_API_KEY') or os.getenv('OPENAI_KEY')
            base_url = os.getenv('OPENAI_BASE_URL')
        except Exception:
            api_key = None
        if api_key:
            try:
                from openai import OpenAI
                kwargs = {'api_key': api_key}
                if base_url:
                    kwargs['base_url'] = base_url
                self._llm_client = OpenAI(**kwargs)
                self._llm_model = os.getenv('OPENAI_MODEL')
            except Exception:
                self._llm_client = None
        self.llm_available = self._llm_client is not None

    def llm_chat(self, messages: List[Dict[str, str]], model: Optional[str] = None,
                 temperature: float = 0.7, max_tokens: Optional[int] = None) -> Optional[str]:
        if not self.llm_available:
            return None
        use_model = model or self._llm_model
        if not use_model:
            raise ValueError('未指定模型名称，且环境变量 OPENAI_MODEL 未设置')
        try:
            resp = self._llm_client.chat.completions.create(
                model=use_model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            if resp and resp.choices:
                return resp.choices[0].message.content
        except Exception as e:
            return None
        return None

    def astrology_describe(self,
                           chart: ChartResult,
                           model: Optional[str] = None,
                           language: str = 'zh',
                           system_prompt: Optional[str] = None) -> AstrologyDesc:
        if not self.llm_available:
            raise RuntimeError('LLM 不可用：请设置 OPENAI_API_KEY 并确保网络可访问。')
        base_prompt = system_prompt or BASE_PROMPTS.get(language.split('-')[0], BASE_PROMPTS['en'])
        chart_text = chart_to_text(chart)
        messages = [
            {'role': 'system', 'content': base_prompt},
            {'role': 'user', 'content': chart_text},
        ]
        response = self.llm_chat(messages, model=model)
        if not response:
            raise RuntimeError('LLM 调用失败或返回空响应。')
        return AstrologyDesc(
            text=response,
            model_used=model or self._llm_model,
            language=language,
            chart_snapshot={},
        )

    def generate_chart(self,
                       birth_dt_input: Any,
                       latitude: float = 39.9042,
                       longitude: float = 116.4074,
                       house_system: str = 'placidus',
                       aspect_orbs: Optional[Dict[str, float]] = None,
                       rulers_scheme: str = 'traditional') -> ChartResult:
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

        planet_longitudes: Dict[str, float] = {}
        if not self.available_skyfield:
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
                except Exception as e:
                    import warnings
                    warnings.warn(f"Planet {name} calculation failed: {e}")

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
        return ChartResult(
            input=input_model,
            settings=settings_model,
            ascendant=ascendant_model,
            houses=houses_list,
            planets=planets_dict,
            aspects=aspects_list,
            mutual_receptions=mutual_receptions_list,
        )

if __name__ == "__main__":
    import zoneinfo
    tz = zoneinfo.ZoneInfo("Asia/Shanghai")
    dt = datetime(1990, 5, 17, 14, 30, tzinfo=tz)
    b = Bersona()
    chart = b.generate_chart(dt, 31.2304, 121.4737)
    print(chart.model_dump_json(indent=2, ensure_ascii=False))
