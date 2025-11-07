from typing import Any, Optional, List
from pydantic import BaseModel

class SuccessResponse(BaseModel):
    success: bool = True
    data: Any
    message: Optional[str] = None

class ErrorResponse(BaseModel):
    success: bool = False
    error: str
    details: Optional[Any] = None

class PaginatedResponse(BaseModel):
    success: bool = True
    items: List[Any]
    total: int
    page: int
    page_size: int
    total_pages: int

def success_response(data: Any, message: str = None) -> dict:
    return {"success": True, "data": data, "message": message}

def error_response(error: str, details: Any = None) -> dict:
    return {"success": False, "error": error, "details": details}

def paginated_response(items: List[Any], total: int, page: int, page_size: int) -> dict:
    return {
        "success": True,
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size
    }
