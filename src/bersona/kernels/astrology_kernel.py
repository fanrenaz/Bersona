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
    """
    Calculates the sun sign based on the user's birth date.
    """

    def calculate(self, birth_date: date, birth_time: "time | None" = None, location: "tuple[float, float] | None" = None) -> dict:
        """
        Determines the sun sign from the birth date.

        :param birth_date: The birth date of the user.
        :return: A dictionary containing the sun sign.
        """
        # --- High-Fidelity Mode ---
        if birth_time is not None or location is not None:
            birth_time, location = get_defaults(birth_time, location)
            
            # Convert local birth time to UTC
            tz_str = get_timezone_str(location[0], location[1])
            local_tz = pytz.timezone(tz_str)
            local_dt = local_tz.localize(datetime.combine(birth_date, birth_time))
            utc_dt = local_dt.astimezone(pytz.utc)
            
            # Set Swiss Ephemeris path
            swe.set_ephe_path('/usr/share/sweph/ephe') # Adjust this path if necessary

            # Calculate Julian Day
            jd = swe.utc_to_jd(utc_dt.year, utc_dt.month, utc_dt.day, utc_dt.hour, utc_dt.minute, utc_dt.second, 1)[1]

            # Calculate Ascendant and houses
            houses = swe.houses(jd, location[0], location[1], b'P')
            ascendant_longitude = houses[0][0]
            ascendant_sign = ZODIAC_SIGNS[int(ascendant_longitude / 30)]

            # Calculate planets
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

        # --- Baseline Mode (Sun Sign only) ---
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
