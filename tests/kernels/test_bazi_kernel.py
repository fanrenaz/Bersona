import unittest
from datetime import date
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


if __name__ == '__main__':
    unittest.main()
