import zoneinfo
from datetime import datetime

from bersona import Bersona

def test_basic_chart_generation():
    tz = zoneinfo.ZoneInfo("Asia/Shanghai")
    dt = datetime(1990, 5, 17, 14, 30, tzinfo=tz)
    b = Bersona()
    chart = b.generate_chart(dt, 31.2304, 121.4737)
    assert chart.planets, "Planets should not be empty"
    assert chart.input.birth_datetime == dt
