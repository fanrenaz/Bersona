import unittest
from datetime import date
from bersona.kernels.astrology_kernel import AstrologyKernel


class TestAstrologyKernel(unittest.TestCase):
    def setUp(self):
        self.kernel = AstrologyKernel()

    def test_calculate_sun_sign(self):
        test_cases = {
            "Aries": date(2024, 3, 21),
            "Taurus": date(2024, 4, 20),
            "Gemini": date(2024, 5, 21),
            "Cancer": date(2024, 6, 22),
            "Leo": date(2024, 7, 23),
            "Virgo": date(2024, 8, 23),
            "Libra": date(2024, 9, 23),
            "Scorpio": date(2024, 10, 24),
            "Sagittarius": date(2024, 11, 23),
            "Capricorn": date(2024, 12, 22),
            "Aquarius": date(2024, 1, 20),
            "Pisces": date(2024, 2, 19),
        }

        for sign, dt in test_cases.items():
            with self.subTest(sign=sign, date=dt):
                result = self.kernel.calculate(dt)
                self.assertEqual(result, {"sun_sign": sign})

    def test_boundary_dates(self):
        # Test boundary between Pisces and Aries
        self.assertEqual(self.kernel.calculate(date(2024, 3, 20))['sun_sign'], "Pisces")
        self.assertEqual(self.kernel.calculate(date(2024, 3, 21))['sun_sign'], "Aries")

        # Test boundary between Capricorn and Aquarius
        self.assertEqual(self.kernel.calculate(date(2024, 1, 19))['sun_sign'], "Capricorn")
        self.assertEqual(self.kernel.calculate(date(2024, 1, 20))['sun_sign'], "Aquarius")

    def test_leap_year(self):
        # February 29th in a leap year
        self.assertEqual(self.kernel.calculate(date(2024, 2, 29))['sun_sign'], "Pisces")


if __name__ == '__main__':
    unittest.main()
