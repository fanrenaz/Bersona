# ...migrated content...
"""占星相关常量定义模块"""
from typing import Dict, List, Tuple

ZODIAC_SIGNS: List[Tuple[str, int]] = [
    ("Aries", 0), ("Taurus", 30), ("Gemini", 60), ("Cancer", 90),
    ("Leo", 120), ("Virgo", 150), ("Libra", 180), ("Scorpio", 210),
    ("Sagittarius", 240), ("Capricorn", 270), ("Aquarius", 300), ("Pisces", 330)
]

TRADITIONAL_RULERS: Dict[str, str] = {
    "Aries": "Mars", "Taurus": "Venus", "Gemini": "Mercury", "Cancer": "Moon",
    "Leo": "Sun", "Virgo": "Mercury", "Libra": "Venus", "Scorpio": "Mars",
    "Sagittarius": "Jupiter", "Capricorn": "Saturn", "Aquarius": "Saturn", "Pisces": "Jupiter"
}

MODERN_RULERS: Dict[str, str] = {
    **TRADITIONAL_RULERS,
    "Scorpio": "Pluto",
    "Aquarius": "Uranus",
    "Pisces": "Neptune"
}

MAJOR_ASPECTS_DEFAULT_ORBS: Dict[str, float] = {
    "Conjunction": 8.0,
    "Opposition": 8.0,
    "Trine": 7.0,
    "Square": 6.0,
    "Sextile": 4.0,
}

ASPECT_DEGREES: Dict[str, float] = {
    "Conjunction": 0.0,
    "Sextile": 60.0,
    "Square": 90.0,
    "Trine": 120.0,
    "Opposition": 180.0,
}

PLANET_NAMES: List[str] = [
    "Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Uranus", "Neptune", "Pluto"
]
