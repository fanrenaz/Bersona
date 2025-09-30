from datetime import date
from sxtwl import fromSolar

from .base import BaseKernel

# 天干
GAN = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]


class BaziKernel(BaseKernel):
    """
    Calculates the Bazi (八字) day master based on the user's birth date.
    """

    def calculate(self, birth_date: date, **kwargs) -> dict:
        """
        Determines the Bazi day master from the birth date.

        :param birth_date: The birth date of the user.
        :return: A dictionary containing the day master.
        """
        day = fromSolar(birth_date.year, birth_date.month, birth_date.day)
        day_master_gan = GAN[day.getDayGZ().tg]

        # To make it more LLM-friendly, we can add the element type
        element_map = {
            "甲": "木", "乙": "木",
            "丙": "火", "丁": "火",
            "戊": "土", "己": "土",
            "庚": "金", "辛": "金",
            "壬": "水", "癸": "水",
        }
        day_master = f"{day_master_gan}{element_map.get(day_master_gan, '')}"

        return {"day_master": day_master}
