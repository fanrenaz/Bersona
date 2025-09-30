from datetime import date
from .base import BaseKernel


class AstrologyKernel(BaseKernel):
    """
    Calculates the sun sign based on the user's birth date.
    """

    def calculate(self, birth_date: date, **kwargs) -> dict:
        """
        Determines the sun sign from the birth date.

        :param birth_date: The birth date of the user.
        :return: A dictionary containing the sun sign.
        """
        month = birth_date.month
        day = birth_date.day

        if (month == 3 and day >= 21) or (month == 4 and day <= 19):
            sign = "Aries"
        elif (month == 4 and day >= 20) or (month == 5 and day <= 20):
            sign = "Taurus"
        elif (month == 5 and day >= 21) or (month == 6 and day <= 21):
            sign = "Gemini"
        elif (month == 6 and day >= 22) or (month == 7 and day <= 22):
            sign = "Cancer"
        elif (month == 7 and day >= 23) or (month == 8 and day <= 22):
            sign = "Leo"
        elif (month == 8 and day >= 23) or (month == 9 and day <= 22):
            sign = "Virgo"
        elif (month == 9 and day >= 23) or (month == 10 and day <= 23):
            sign = "Libra"
        elif (month == 10 and day >= 24) or (month == 11 and day <= 22):
            sign = "Scorpio"
        elif (month == 11 and day >= 23) or (month == 12 and day <= 21):
            sign = "Sagittarius"
        elif (month == 12 and day >= 22) or (month == 1 and day <= 19):
            sign = "Capricorn"
        elif (month == 1 and day >= 20) or (month == 2 and day <= 18):
            sign = "Aquarius"
        else:  # (month == 2 and day >= 19) or (month == 3 and day <= 20)
            sign = "Pisces"

        return {"sun_sign": sign}
