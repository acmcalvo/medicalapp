from typing import Literal

from pydantic import BaseModel, Field

Severity = Literal["contraindicated", "major", "moderate", "minor", "none"]
Role = Literal["doctor", "pharmacist"]


class MedicationInput(BaseModel):
    name_entered: str
    dose: str | None = None
    route: str | None = None
    frequency: str | None = None


class PatientContext(BaseModel):
    age: int | None = None
    pregnancy_status: Literal["pregnant", "not_pregnant", "unknown"] = "unknown"
    egfr: float | None = Field(default=None, description="Kidney function estimate")
    liver_impairment: Literal["none", "mild", "moderate", "severe", "unknown"] = "unknown"
    allergies: list[str] = Field(default_factory=list)


class InteractionItem(BaseModel):
    drug_a: str
    drug_b: str
    severity: Severity
    source_type: Literal["live_rxcui", "heuristic"]
    mechanism: str
    clinical_effect: str
    recommendation: str
    monitoring: list[str]
    source: str


class InteractionCheckRequest(BaseModel):
    medications: list[MedicationInput]
    patient: PatientContext


class InteractionCheckResponse(BaseModel):
    max_severity: Severity
    interactions: list[InteractionItem]
    requires_clinician_review: bool


class AdviceRequest(BaseModel):
    role: Role
    interactions: list[InteractionItem]
    patient: PatientContext
    question: str | None = None


class AdviceResponse(BaseModel):
    summary: str
    action_plan: list[str]
    alternatives: list[str]
    red_flags: list[str]
    citations: list[str]
    disclaimer: str
