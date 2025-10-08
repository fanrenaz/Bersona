from bersona.structuring.fallback import build_fallback_persona

print('--- Aries fallback ---')
print(build_fallback_persona({'astrology_raw': {'sun_sign': 'Aries'}}).model_dump())
print('\n--- Geng Metal fallback (bazi) ---')
print(build_fallback_persona({'bazi_raw': {'day_master': 'Geng Metal'}}).model_dump())
print('\n--- Unknown fallback ---')
print(build_fallback_persona({}).model_dump())
