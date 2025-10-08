from bersona.structuring.parser import parse_structured_output, build_structured_persona
from bersona.structuring.schemas import StructuredPersonaFeatures

raw = '{"core_identity":"细致分析","motivation":"改进","decision_style":"逻辑","social_style":"克制","strength_traits":["分析","责任"],"growth_opportunities":["放松"],"advanced":{}}'
cleaned, meta = parse_structured_output(raw)
obj = build_structured_persona(cleaned, meta)
print('meta=', meta)
print('persona=', obj.model_dump())
