from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from typing import List
from pydantic import BaseModel
from auth.models import User
from models.app_role import AppRole
from middleware.auth import get_current_user, require_app_role
from .models import Policy, Claim, ClaimDocument, ClaimNote, ClaimStatus
from .schemas import (
    PolicyCreate, PolicyResponse, ClaimCreate, ClaimUpdate, ClaimResponse,
    ClaimNoteCreate, ClaimNoteResponse, AppRoleAssign
)
from .workflow import can_transition_status
from services.ai_service import AIService
import uuid
import os

router = APIRouter()

class RewriteRequest(BaseModel):
    text: str
    model: str = "gemini"

# Auto-assign customer role on first access
async def ensure_customer_role(user: User):
    """Auto-assign customer role if user has no roles in insurance-claims"""
    existing_roles = await AppRole.filter(user_id=user.id, app_name="insurance-claims")
    if not existing_roles:
        await AppRole.create(user_id=user.id, app_name="insurance-claims", role="customer")

@router.get("/access")
async def check_access(current_user: User = Depends(get_current_user)):
    """Check if user has access to insurance claims app"""
    await ensure_customer_role(current_user)
    app_roles = await AppRole.filter(user_id=current_user.id, app_name="insurance-claims")
    return {"roles": [ar.role for ar in app_roles]}

@router.post("/policies", response_model=PolicyResponse)
async def create_policy(
    policy: PolicyCreate,
    current_user: User = Depends(require_app_role("insurance-claims", ["customer", "agent", "admin"]))
):
    policy_number = f"POL-{uuid.uuid4().hex[:8].upper()}"
    new_policy = await Policy.create(
        policy_number=policy_number,
        customer_id=current_user.id,
        **policy.dict()
    )
    return PolicyResponse(**new_policy.__dict__)

@router.get("/policies", response_model=List[PolicyResponse])
async def get_policies(current_user: User = Depends(get_current_user)):
    await ensure_customer_role(current_user)
    
    if current_user.global_role == "admin":
        policies = await Policy.all()
    else:
        policies = await Policy.filter(customer_id=current_user.id)
    
    return [PolicyResponse(**p.__dict__) for p in policies]

@router.post("/claims", response_model=ClaimResponse)
async def create_claim(
    claim: ClaimCreate,
    current_user: User = Depends(require_app_role("insurance-claims", ["customer", "agent", "admin"]))
):
    policy = await Policy.get_or_none(id=claim.policy_id)
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    
    claim_number = f"CLM-{uuid.uuid4().hex[:8].upper()}"
    new_claim = await Claim.create(
        claim_number=claim_number,
        policy_id=claim.policy_id,
        customer_id=policy.customer_id,
        incident_date=claim.incident_date,
        incident_description=claim.incident_description,
        incident_location=claim.incident_location
    )
    return ClaimResponse(**new_claim.__dict__)

@router.get("/claims", response_model=List[ClaimResponse])
async def get_claims(current_user: User = Depends(get_current_user)):
    await ensure_customer_role(current_user)
    
    # Get user's app roles
    app_roles = await AppRole.filter(user_id=current_user.id, app_name="insurance-claims")
    user_roles = [ar.role for ar in app_roles]
    
    # Admin sees all
    if current_user.global_role == "admin":
        claims = await Claim.all()
    # Customer sees only their claims
    elif "customer" in user_roles and len(user_roles) == 1:
        claims = await Claim.filter(customer_id=current_user.id)
    # Agent sees submitted and under_review
    elif "agent" in user_roles:
        claims = await Claim.filter(status__in=[ClaimStatus.SUBMITTED, ClaimStatus.UNDER_REVIEW])
    # Adjuster sees assigned to them
    elif "adjuster" in user_roles:
        claims = await Claim.filter(assigned_adjuster_id=current_user.id)
    # Manager sees claims needing assignment or settlement
    elif "manager" in user_roles:
        claims = await Claim.filter(status__in=[ClaimStatus.UNDER_REVIEW, ClaimStatus.ASSIGNED, ClaimStatus.INVESTIGATING, ClaimStatus.APPROVED])
    else:
        claims = []
    
    return [ClaimResponse(**c.__dict__) for c in claims]

@router.get("/claims/{claim_id}", response_model=ClaimResponse)
async def get_claim(
    claim_id: int,
    current_user: User = Depends(get_current_user)
):
    claim = await Claim.get_or_none(id=claim_id)
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    
    # Check access
    app_roles = await AppRole.filter(user_id=current_user.id, app_name="insurance-claims")
    user_roles = [ar.role for ar in app_roles]
    
    if current_user.global_role != "admin":
        if "customer" in user_roles and claim.customer_id != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied")
        if "adjuster" in user_roles and claim.assigned_adjuster_id != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied")
    
    return ClaimResponse(**claim.__dict__)

@router.put("/claims/{claim_id}/status")
async def update_claim_status(
    claim_id: int,
    update: ClaimUpdate,
    current_user: User = Depends(get_current_user)
):
    claim = await Claim.get_or_none(id=claim_id)
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    
    # Get user's app roles
    app_roles = await AppRole.filter(user_id=current_user.id, app_name="insurance-claims")
    user_roles = [ar.role for ar in app_roles]
    
    # Validate status transition
    if update.status and update.status != claim.status:
        if not can_transition_status(claim.status, update.status, user_roles, current_user.global_role == "admin"):
            raise HTTPException(
                status_code=403,
                detail=f"Cannot transition from {claim.status} to {update.status} with roles {user_roles}"
            )
        claim.status = update.status
    
    if update.estimated_damage is not None:
        claim.estimated_damage = update.estimated_damage
    if update.approved_amount is not None:
        claim.approved_amount = update.approved_amount
    if update.assigned_adjuster_id is not None:
        claim.assigned_adjuster_id = update.assigned_adjuster_id
    
    await claim.save()
    return {"message": "Claim updated successfully"}

@router.get("/adjusters")
async def get_adjusters(
    current_user: User = Depends(require_app_role("insurance-claims", ["manager", "admin"]))
):
    """Get list of users with adjuster role"""
    adjuster_roles = await AppRole.filter(app_name="insurance-claims", role="adjuster")
    adjuster_ids = [ar.user_id for ar in adjuster_roles]
    adjusters = await User.filter(id__in=adjuster_ids, is_active=True)
    return [{"id": u.id, "name": u.username} for u in adjusters]

@router.post("/claims/{claim_id}/notes", response_model=ClaimNoteResponse)
async def add_note(
    claim_id: int,
    note: ClaimNoteCreate,
    current_user: User = Depends(get_current_user)
):
    claim = await Claim.get_or_none(id=claim_id)
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    
    new_note = await ClaimNote.create(
        claim_id=claim_id,
        author_id=current_user.id,
        content=note.content
    )
    return ClaimNoteResponse(**new_note.__dict__)

@router.get("/claims/{claim_id}/notes", response_model=List[ClaimNoteResponse])
async def get_notes(
    claim_id: int,
    current_user: User = Depends(get_current_user)
):
    notes = await ClaimNote.filter(claim_id=claim_id)
    return [ClaimNoteResponse(**n.__dict__) for n in notes]

# Admin endpoints
@router.post("/admin/assign-role")
async def assign_role(
    assignment: AppRoleAssign,
    current_user: User = Depends(get_current_user)
):
    if current_user.global_role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Check if role already exists
    existing = await AppRole.get_or_none(
        user_id=assignment.user_id,
        app_name=assignment.app_name,
        role=assignment.role
    )
    if existing:
        return {"message": "Role already assigned"}
    
    await AppRole.create(**assignment.dict())
    return {"message": "Role assigned successfully"}

@router.post("/rewrite")
async def rewrite_text(
    request: RewriteRequest,
    current_user: User = Depends(get_current_user)
):
    """Rewrite text using AI for insurance claims"""
    ai_service = AIService()
    prompt = f"Rewrite this insurance claim text professionally and clearly. Keep it concise but detailed:\n\n{request.text}"
    
    response = await ai_service.generate_response(
        prompt=prompt,
        model_name=request.model
    )
    
    return {"rewritten_text": response}
