import swisseph as swe
from datetime import date, datetime, time, timezone
import pytz
from ..utils.location import get_timezone_str, get_defaults
from .base import BaseKernel

# Planet names mapping
PLANET_NAMES = {
    swe.SUN: "Sun",
    swe.MOON: "Moon",
    swe.MERCURY: "Mercury",
    swe.VENUS: "Venus",
    swe.MARS: "Mars",
    swe.JUPITER: "Jupiter",
    swe.SATURN: "Saturn",
    swe.URANUS: "Uranus",
    swe.NEPTUNE: "Neptune",
    swe.PLUTO: "Pluto",
}

# Zodiac signs
ZODIAC_SIGNS = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"
]


class AstrologyKernel(BaseKernel):
    """高保真占星内核：始终使用瑞士星历计算太阳、月亮、上升以及行星所处星座。

    如果未提供具体出生时间或地点，使用 `utils.location.get_defaults` 中的默认值进行推断，
    不再退化到仅基于日期的太阳星座分段法。这样可以保持统一的输出结构，方便下游结构化与人格生成阶段。
    """

    def calculate(self, birth_date: date, birth_time: "time | None" = None, location: "tuple[float, float] | None" = None) -> dict:
        """计算完整星盘核心字段。

        返回字段：
        - sun_sign: 太阳星座
        - moon_sign: 月亮星座
        - ascendant_sign: 上升星座
        - planets: 其余行星到星座的映射（不含 Sun/Moon）
        """
        # 统一进入高保真模式，填充默认时间与地点
        birth_time, location = get_defaults(birth_time, location)

        # 将本地时间转换为 UTC
        tz_str = get_timezone_str(location[0], location[1])
        local_tz = pytz.timezone(tz_str)
        local_dt = local_tz.localize(datetime.combine(birth_date, birth_time))
        utc_dt = local_dt.astimezone(pytz.utc)

        # 设置星历路径（容器或宿主系统需确保 ephe 目录存在）
        swe.set_ephe_path('/usr/share/sweph/ephe')  # TODO: 可参数化或通过环境变量配置

        # 计算儒略日
        jd = swe.utc_to_jd(utc_dt.year, utc_dt.month, utc_dt.day, utc_dt.hour, utc_dt.minute, utc_dt.second, 1)[1]

        # 计算宫位与上升星座
        houses = swe.houses(jd, location[0], location[1], b'P')
        ascendant_longitude = houses[0][0]
        ascendant_sign = ZODIAC_SIGNS[int(ascendant_longitude / 30)]

        # 计算各行星位置
        planets = {}
        for planet_id, planet_name in PLANET_NAMES.items():
            planet_pos = swe.calc_ut(jd, planet_id)[0]
            sign_index = int(planet_pos[0] / 30)
            planets[planet_name] = ZODIAC_SIGNS[sign_index]

        return {
            "sun_sign": planets.pop("Sun"),
            "moon_sign": planets.pop("Moon"),
            "ascendant_sign": ascendant_sign,
            "planets": planets
        }
