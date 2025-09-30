from datetime import date
from sxtwl import fromSolar

from .base import BaseKernel
from ..utils.location import get_defaults

# 天干
GAN = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]

# 地支
ZHI = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]


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

            return {
                "day_master": day_master,
                "four_pillars": {
                    "year": f"{year_gan}{year_zhi}",
                    "month": f"{month_gan}{month_zhi}",
                    "day": f"{day_gan}{day_zhi}",
                    "hour": f"{hour_gan}{hour_zhi}",
                }
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
