from __future__ import annotations

from datetime import datetime
from typing import List, Literal, Optional, Tuple
from uuid import UUID

from pydantic import BaseModel, Field


class Segmentation(BaseModel):
    polygon: List[Tuple[float, float]]


class DefectInfo(BaseModel):
    type: str
    confidence: float
    segmentation: Optional[Segmentation] = None


class BBox(BaseModel):
    x_min: float
    y_min: float
    x_max: float
    y_max: float


class FruitSummary(BaseModel):
    fruit_id: str = Field(alias="fruit_id")
    fruit_class: Literal["apple", "banana", "tomato"]
    confidence: float
    bbox: BBox
    defects: List[DefectInfo] = Field(default_factory=list)


class ScanResult(BaseModel):
    session_id: UUID
    image_id: str
    timestamp: datetime
    weight_grams: float
    fruits: List[FruitSummary] = Field(default_factory=list)


