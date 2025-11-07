from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from .models import ClaimStatus

class PolicyCreate(BaseModel):
    vehicle_make: str
    vehicle_model: str
    vehicle_year: int
    license_plate: str
    coverage_amount: float

class PolicyResponse(BaseModel):
    id: int
    policy_number: str
    vehicle_make: str
    vehicle_model: str
    vehicle_year: int
    license_plate: str
    coverage_amount: float
    is_active: bool
    created_at: datetime

class ClaimCreate(BaseModel):
    policy_id: int
    incident_date: datetime
    incident_description: str
    incident_location: str

class ClaimUpdate(BaseModel):
    status: Optional[ClaimStatus] = None
    assigned_adjuster_id: Optional[int] = None
    estimated_damage: Optional[float] = None
    approved_amount: Optional[float] = None

class ClaimResponse(BaseModel):
    id: int
    claim_number: str
    policy_id: int
    customer_id: int
    assigned_adjuster_id: Optional[int]
    status: ClaimStatus
    incident_date: datetime
    incident_description: str
    incident_location: str
    estimated_damage: Optional[float]
    approved_amount: Optional[float]
    created_at: datetime

class ClaimNoteCreate(BaseModel):
    content: str

class ClaimNoteResponse(BaseModel):
    id: int
    content: str
    author_id: int
    created_at: datetime

class AppRoleAssign(BaseModel):
    user_id: int
    app_name: str
    role: str
