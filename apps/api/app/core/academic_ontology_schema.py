from __future__ import annotations

from typing import List, Literal

from pydantic import BaseModel, Field


EntityType = Literal["method", "task", "dataset", "metric", "baseline", "limitation"]
RelationType = Literal[
    "applies_to_task",
    "evaluated_on_dataset",
    "improves_metric_on_dataset",
    "compares_against_baseline",
    "has_limitation",
]


class AcademicEntity(BaseModel):
    entity_id: str = Field(..., min_length=1)
    entity_type: EntityType
    name: str = Field(..., min_length=1)


class AcademicRelation(BaseModel):
    relation_id: str = Field(..., min_length=1)
    subject_id: str = Field(..., min_length=1)
    relation_type: RelationType
    object_id: str = Field(..., min_length=1)


class PaperGraphSlice(BaseModel):
    paper_id: str = Field(..., min_length=1)
    entities: List[AcademicEntity] = Field(default_factory=list)
    relations: List[AcademicRelation] = Field(default_factory=list)


class GraphRetrievalResult(BaseModel):
    used: bool = False
    candidate_count: int = 0
    candidates: List[dict] = Field(default_factory=list)
    merge_gain: float = 0.0
