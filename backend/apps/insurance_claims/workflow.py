from .models import ClaimStatus

def can_transition_status(current_status: ClaimStatus, new_status: ClaimStatus, user_roles: list, is_admin: bool = False) -> bool:
    """Validate workflow transitions based on user roles"""
    
    # Admins can do anything
    if is_admin:
        return True
    
    # Define allowed transitions per role
    transitions = {
        ClaimStatus.SUBMITTED: {
            "agent": [ClaimStatus.UNDER_REVIEW, ClaimStatus.REJECTED],
            "manager": [ClaimStatus.UNDER_REVIEW, ClaimStatus.ASSIGNED, ClaimStatus.REJECTED],
        },
        ClaimStatus.UNDER_REVIEW: {
            "agent": [ClaimStatus.REJECTED],
            "manager": [ClaimStatus.ASSIGNED, ClaimStatus.REJECTED],
        },
        ClaimStatus.ASSIGNED: {
            "adjuster": [ClaimStatus.INVESTIGATING, ClaimStatus.REJECTED],
            "manager": [ClaimStatus.INVESTIGATING, ClaimStatus.REJECTED],
        },
        ClaimStatus.INVESTIGATING: {
            "adjuster": [ClaimStatus.APPROVED, ClaimStatus.REJECTED],
            "manager": [ClaimStatus.APPROVED, ClaimStatus.REJECTED],
        },
        ClaimStatus.APPROVED: {
            "manager": [ClaimStatus.SETTLED],
        },
        ClaimStatus.REJECTED: {},
        ClaimStatus.SETTLED: {}
    }
    
    allowed_transitions = transitions.get(current_status, {})
    
    # Check if any of user's roles allow this transition
    for role in user_roles:
        if new_status in allowed_transitions.get(role, []):
            return True
    
    return False
