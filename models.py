"""Pydantic 数据模型定义"""
from __future__ import annotations
from datetime import datetime
from typing import List, Dict, Optional, Tuple, Any
from pydantic import BaseModel, Field, field_validator

class ChartInput(BaseModel):
    birth_datetime: datetime = Field(description="出生时间，需 timezone-aware")
    latitude: float = Field(ge=-90, le=90, description="纬度")
    longitude: float = Field(ge=-180, le=180, description="经度 (东正西负)")
    house_system: str = Field(default='equal', description="宫位系统 'equal' 或 'placidus'")
    rulers_scheme: str = Field(default='traditional', description="主宰体系 'traditional' 或 'modern'")
    aspect_orbs: Optional[Dict[str, float]] = Field(default=None, description="相位容许度覆盖表")
    date_only: bool = Field(default=False, description="输入是否为仅日期（自动补 12:00），若 True 则不计算 Asc 与 Houses")

    @field_validator('birth_datetime')
    def _tz_required(cls, v: datetime):
        if v.tzinfo is None:
            raise ValueError('datetime 必须带时区信息')
        return v

    @field_validator('house_system')
    def _house_system_ok(cls, v: str):
        if v not in ('equal', 'placidus'):
            raise ValueError("house_system 仅支持 'equal' 或 'placidus'")
        return v

    @field_validator('rulers_scheme')
    def _rulers_scheme_ok(cls, v: str):
        if v not in ('traditional', 'modern'):
            raise ValueError("rulers_scheme 仅支持 'traditional' 或 'modern'")
        return v

class Ascendant(BaseModel):
    longitude: float
    sign: str

class HouseCusp(BaseModel):
    house: int = Field(ge=1, le=12)
    cusp_longitude: float
    cusp_sign: str

class PlanetPosition(BaseModel):
    name: str
    ecliptic_longitude: float
    ecliptic_latitude: float
    sign: str
    retrograde: bool

class Aspect(BaseModel):
    planet1: str
    planet2: str
    aspect: str
    separation: float = Field(description="两行星最小分离角 (0-180)")
    difference: float = Field(description="与标准相位角的差值")
    orb_allowed: float

class MutualReception(BaseModel):
    planet1: str
    planet2: str
    scheme: str
    signs: Tuple[str, str]

class ChartSettings(BaseModel):
    house_system: str
    rulers_scheme: str
    aspect_orbs: Dict[str, float]
    libraries: Dict[str, bool]

class ChartResult(BaseModel):
    input: ChartInput
    settings: ChartSettings
    ascendant: Optional[Ascendant] = None
    houses: List[HouseCusp] = []
    planets: Dict[str, PlanetPosition]
    aspects: List[Aspect]
    mutual_receptions: List[MutualReception]

    def summary(self) -> Dict[str, int]:
        return {
            'planets': len(self.planets),
            'aspects': len(self.aspects),
            'mutual_receptions': len(self.mutual_receptions)
        }


class AstrologyDesc(BaseModel):
    """LLM 生成的占星解释描述。"""
    text: str = Field(description="自然语言描述")
    model_used: Optional[str] = Field(default=None, description="使用的 LLM 模型名称")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="UTC 创建时间")
    language: str = Field(default='zh', description="描述语言标记")
    chart_snapshot: Dict[str, Any] = Field(default_factory=dict, description="星盘摘要或关键信息快照")

    def short(self) -> str:
        return self.text[:120] + ('...' if len(self.text) > 120 else '')
