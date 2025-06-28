from pydantic import BaseModel
from typing import Optional

class CallState(BaseModel):
    visit_limit: Optional[int] = None
    visit_limit_structure: Optional[str] = None
    visits_used: Optional[int] = None
    copay: Optional[float] = None
    deductible: Optional[float] = None
    deductible_met: Optional[float] = None
    oop_max: Optional[float] = None
    oop_met: Optional[float] = None
    authorization_required: Optional[bool] = None
    reference_number: Optional[str] = None

class PatientInfo(BaseModel):
    name: str = "John Doe"
    date_of_birth: str = "January 1st 1980"
    member_id: str = "M O Y 1 2 3 4 5 6 7 8 9"
    active_date: str = "12/31/2024"
    date_of_treatment: str = "06/15/2024"

# Call state field explanations
CALL_STATE_EXPLANATIONS = {
    "visit_limit": "Whether the visits are limited, and the allowed number.",
    "visit_limit_structure": "How the limit is tracked (calendar year, fiscal year, benefit period, etc.) (only if a visit limit exists)",
    "visits_used": "How many visits have been used prior to this contact (only if a visit limit exists)",
    "copay": "The copay amount per visit.",
    "deductible": "Whether there is a deductible, and the total amount.",
    "deductible_met": "How much of the deductible has been met (only if a deductible exists)",
    "oop_max": "Whether there's a cap on out-of-pocket expenses, and the total amount.",
    "oop_met": "How much has already been paid toward the out-of-pocket max (only if applicable)",
    "authorization_required": "Whether pre-authorization is required before beginning care.",
    "reference_number": "The reference number for this call or authorization."
} 