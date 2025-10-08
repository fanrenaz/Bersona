from bersona.llm.prompts import STRUCTURE_PROMPT_TEMPLATE
import json

raw_symbols = {"astrology_raw": {"sun_sign": "Virgo"}}
rendered = STRUCTURE_PROMPT_TEMPLATE.replace('{raw_symbols_json}', json.dumps(raw_symbols, ensure_ascii=False))
print(rendered[:500] + '\n...\n')
