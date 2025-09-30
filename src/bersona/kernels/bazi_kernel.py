from datetime import date
from sxtwl import fromSolar

from .base import BaseKernel
from ..utils.location import get_defaults

# 天干
GAN = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]

# 地支
ZHI = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]

# Ten Gods mapping
TEN_GODS_MAP = {
    "比肩": "Friend",
    "劫财": "Rob Wealth",
    "食神": "Eating God",
    "伤官": "Hurting Officer",
    "偏财": "Indirect Wealth",
    "正财": "Direct Wealth",
    "七杀": "Seven Killings",
    "正官": "Direct Officer",
    "偏印": "Indirect Resource",
    "正印": "Direct Resource",
}

# Heavenly Stem properties (Element, Yin/Yang)
GAN_PROPERTIES = {
    "甲": {"element": "木", "yin_yang": "yang"},
    "乙": {"element": "木", "yin_yang": "yin"},
    "丙": {"element": "火", "yin_yang": "yang"},
    "丁": {"element": "火", "yin_yang": "yin"},
    "戊": {"element": "土", "yin_yang": "yang"},
    "己": {"element": "土", "yin_yang": "yin"},
    "庚": {"element": "金", "yin_yang": "yang"},
    "辛": {"element": "金", "yin_yang": "yin"},
    "壬": {"element": "水", "yin_yang": "yang"},
    "癸": {"element": "水", "yin_yang": "yin"},
}

# Five Elements relationships
FIVE_ELEMENTS_REL = {
    "木": {"produces": "火", "controls": "土"},
    "火": {"produces": "土", "controls": "金"},
    "土": {"produces": "金", "controls": "水"},
    "金": {"produces": "水", "controls": "木"},
    "水": {"produces": "木", "controls": "火"},
}


class BaziKernel(BaseKernel):
    """
    Calculates the Bazi (八字) day master based on the user's birth date.
    """

    def calculate(self, birth_date: date, birth_time: "time | None" = None, location: "tuple[float, float] | None" = None) -> dict:
        """
        Determines the Bazi day master from the birth date.

        :param birth_date: The birth date of the user.
        :return: A dictionary containing the day master.
        """
                # --- High-Fidelity Mode ---
        if birth_time is not None:
            day = fromSolar(birth_date.year, birth_date.month, birth_date.day)
            
            year_gan = GAN[day.getYearGZ().tg]
            year_zhi = ZHI[day.getYearGZ().dz]
            
            month_gan = GAN[day.getMonthGZ().tg]
            month_zhi = ZHI[day.getMonthGZ().dz]

            day_gan_idx = day.getDayGZ().tg
            day_gan = GAN[day_gan_idx]
            day_zhi = ZHI[day.getDayGZ().dz]

            hour_zhi_idx = day.getHourGZ(birth_time.hour).dz
            hour_gan = self._get_hour_gan(day_gan, ZHI[hour_zhi_idx])
            hour_zhi = ZHI[hour_zhi_idx]

            day_master = f"{day_gan}{self._get_element(day_gan)}"

            # Calculate Ten Gods
            ten_gods = {
                "year": self._calculate_ten_gods(day_gan, year_gan),
                "month": self._calculate_ten_gods(day_gan, month_gan),
                "hour": self._calculate_ten_gods(day_gan, hour_gan),
            }

            return {
                "day_master": day_master,
                "four_pillars": {
                    "year": f"{year_gan}{year_zhi}",
                    "month": f"{month_gan}{month_zhi}",
                    "day": f"{day_gan}{day_zhi}",
                    "hour": f"{hour_gan}{hour_zhi}",
                },
                "ten_gods": ten_gods
            }

        # --- Baseline Mode (Day Master only) ---
        day = fromSolar(birth_date.year, birth_date.month, birth_date.day)
        day_master_gan = GAN[day.getDayGZ().tg]
        day_master = f"{day_master_gan}{self._get_element(day_master_gan)}"

        return {"day_master": day_master}

    def _get_hour_gan(self, day_gan: str, hour_zhi: str) -> str:
        """
        Calculates the hour stem (时干) based on the day stem (日干) and hour branch (时支).
        This is the "五鼠遁日起时法".
        """
        # Day stem to starting hour stem mapping (for 子时)
        start_hour_gan_map = {
            "甲": "甲", "己": "甲",
            "乙": "丙", "庚": "丙",
            "丙": "戊", "辛": "戊",
            "丁": "庚", "壬": "庚",
            "戊": "壬", "癸": "壬",
        }
        start_gan = start_hour_gan_map[day_gan]
        
        # Find the starting index in the GAN list
        start_index = GAN.index(start_gan)
        hour_index = ZHI.index(hour_zhi)
        
        # The hour stem index is the starting index + the hour branch index, wrapped around
        gan_index = (start_index + hour_index) % 10
        return GAN[gan_index]

    def _get_element(self, gan: str) -> str:
        element_map = {
            "甲": "木", "乙": "木",
            "丙": "火", "丁": "火",
            "戊": "土", "己": "土",
            "庚": "金", "辛": "金",
            "壬": "水", "癸": "水",
        }
        return element_map.get(gan, '')

    def _calculate_ten_gods(self, day_master_gan: str, other_gan: str) -> str:
        """
        Calculates the Ten God relationship between the day master and another stem.
        """
        dm_props = GAN_PROPERTIES[day_master_gan]
        other_props = GAN_PROPERTIES[other_gan]

        dm_element = dm_props["element"]
        other_element = other_props["element"]
        
        dm_yin_yang = dm_props["yin_yang"]
        other_yin_yang = other_props["yin_yang"]

        if dm_element == other_element:
            return "比肩" if dm_yin_yang != other_yin_yang else "劫财"
        
        # Element that produces me (Mother)
        if FIVE_ELEMENTS_REL[other_element]["produces"] == dm_element:
            return "正印" if dm_yin_yang != other_yin_yang else "偏印"

        # Element I produce (Child)
        if FIVE_ELEMENTS_REL[dm_element]["produces"] == other_element:
            return "伤官" if dm_yin_yang != other_yin_yang else "食神"

        # Element I control (Wealth)
        if FIVE_ELEMENTS_REL[dm_element]["controls"] == other_element:
            return "正财" if dm_yin_yang != other_yin_yang else "偏财"

        # Element that controls me (Power)
        if FIVE_ELEMENTS_REL[other_element]["controls"] == dm_element:
            return "正官" if dm_yin_yang != other_yin_yang else "七杀"
        
        return "" # Should not happen
