import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Contract(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)


class Claim(Contract):
    text: str = Field(min_length=1, max_length=1100)
    evidence_ids: list[str] = Field(min_length=1, max_length=30)


class Recheck(Contract):
    start_ms: float = Field(ge=0, allow_inf_nan=False)
    end_ms: float = Field(gt=0, allow_inf_nan=False)
    reason: str = Field(min_length=1, max_length=500)


class HistoryOutput(Contract):
    observations: list[Claim] = Field(max_length=6)
    limitations: list[str] = Field(max_length=8)


class MotionOutput(HistoryOutput):
    view_status: Literal['clear', 'partial', 'obscured']
    review_status: Literal['no_clear_change', 'review', 'insufficient_view']
    requested_recheck: Recheck | None


class Decision(Contract):
    concern: Literal['routine', 'review', 'insufficient_evidence']
    accepted_evidence_ids: list[str] = Field(max_length=100)
    rejected_evidence_ids: list[str] = Field(max_length=100)
    rationale: list[Claim] = Field(max_length=6)
    limitations: list[str] = Field(max_length=10)


class Narrative(Contract):
    headline: str = Field(min_length=1, max_length=160)
    statements: list[Claim] = Field(max_length=5)
    limitations: list[str] = Field(max_length=8)


class Narratives(Contract):
    analyst: Narrative
    fan: Narrative


class SingleOutput(Contract):
    motion: MotionOutput
    decision: Decision


class AnalysisRequest(Contract):
    scenario_id: Literal['S001', 'S002', 'S003']
    player_id: Literal['P001'] = 'P001'
    client_request_id: str = Field(min_length=1, max_length=100, pattern=r'^[a-zA-Z0-9_-]+$')
    mode: Literal['multi', 'single'] = 'multi'


def validate_claims(value: BaseModel, allowed: set[str]):
    """Citation membership is a boundary check, not a truth or medical assessment."""
    payload = value.model_dump()

    def walk(item):
        if isinstance(item, dict):
            if 'evidence_ids' in item and not set(item['evidence_ids']).issubset(allowed):
                raise ValueError('Unsent or unauthorized evidence citation')
            for child in item.values():
                walk(child)
        elif isinstance(item, list):
            for child in item:
                walk(child)
        elif isinstance(item, str):
            if re.search(r'\d\s*%|\b(?:diagnos\w*|torn|ruptur\w*|injury probability)\b', item, re.I):
                raise ValueError('Unsupported diagnosis or percentage in model output')

    walk(payload)


def validate_window(window: Recheck, duration: float):
    if not 0 <= window.start_ms < window.end_ms <= duration or window.end_ms - window.start_ms > 3000:
        raise ValueError('Recheck must be inside the clip and at most 3000 ms')
