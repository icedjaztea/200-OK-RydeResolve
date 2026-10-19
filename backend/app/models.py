from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Literal, Any

Category = Literal['fare_dispute', 'route_deviation', 'no_show_charge', 'driver_no_show', 'property_damage', 'safety_incident', 'other']

# Categories that a reviewer may reclassify an "other" case into.
ReclassifyCategory = Literal['fare_dispute', 'route_deviation', 'no_show_charge', 'driver_no_show', 'property_damage', 'safety_incident']

class CaseCreate(BaseModel):
    case_id: str = Field(pattern=r'^[A-Za-z0-9_-]{4,80}$')
    trip_id: str = Field(default='DEMO-TRIP')
    counterparty_id: Literal['rider_a','rider_b','driver_a','driver_b'] | None = None
    category: Category
    filed_by: Literal['rider', 'driver'] = 'rider'
    description: str = Field(min_length=5, max_length=3000)
    dispute_amount: float | None = Field(default=None, ge=0, le=100000)
    dispute_value_basis: str = 'disputed_remedy_amount'
    facts: dict[str, Any] = Field(default_factory=dict)
    fraud_flags: int = Field(default=0, ge=0)
    synthetic: bool = True

class ClarificationReply(BaseModel):
    answer: str = Field(min_length=1, max_length=2500)

class ClarificationRequest(BaseModel):
    """Reviewer-created ad-hoc clarification request."""
    recipient: Literal['rider', 'driver']
    question: str = Field(min_length=5, max_length=1000)

class EvidenceUpload(BaseModel):
    field: str = Field(min_length=2, max_length=80)
    value: Any
    provenance: str = Field(min_length=3, max_length=300)
    evidence_timestamp: str | None = None

class ReviewerDecision(BaseModel):
    disposition: Literal['refund', 'no_action', 'credit', 'reject_claim']
    amount: float = Field(default=0, ge=0, le=100000)
    reason: str = Field(min_length=10, max_length=2000)
    proposed_precedent: str | None = None

class LearningApproval(BaseModel):
    rationale: str = Field(min_length=10, max_length=500)

class ReclassifyRequest(BaseModel):
    """Reviewer reclassification of an 'other' case to a specific category."""
    category: ReclassifyCategory
    reason: str = Field(min_length=10, max_length=500)
