import unittest
from datetime import date, time
from bersona.kernels.bazi_kernel import BaziKernel


class TestBaziKernel(unittest.TestCase):
    def setUp(self):
        self.kernel = BaziKernel()

    def test_calculate_day_master(self):
        test_cases = {
            date(1990, 8, 25): "壬水",
            date(2023, 10, 27): "戊土",
            date(1988, 2, 5): "庚金",
        }

        for dt, expected_master in test_cases.items():
            with self.subTest(date=dt, expected=expected_master):
                result = self.kernel.calculate(dt)
                self.assertEqual(result, {"day_master": expected_master})

    def test_high_fidelity_mode(self):
        # Test with a known Bazi chart
                # Mao Zedong: Dec 26, 1893, ~8:00 AM (Chen hour)
        birth_date = date(1893, 12, 26)
        birth_time = time(8, 0) # Chen hour
        
        result = self.kernel.calculate(birth_date, birth_time=birth_time)
        
        # Correct Bazi for Mao Zedong is: 癸巳 甲子 丁酉 甲辰
        self.assertEqual(result['day_master'], '丁火')
        self.assertEqual(result['four_pillars']['year'], '癸巳')
        self.assertEqual(result['four_pillars']['month'], '甲子')
        self.assertEqual(result['four_pillars']['day'], '丁酉')
        self.assertEqual(result['four_pillars']['hour'], '甲辰')

        # Verify Ten Gods
        self.assertEqual(result['ten_gods']['year'], '七杀')
        self.assertEqual(result['ten_gods']['month'], '正印')
        self.assertEqual(result['ten_gods']['hour'], '正印')


if __name__ == '__main__':
    unittest.main()
