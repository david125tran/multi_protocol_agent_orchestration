# app/protocols/rest/router_rest.py

# Imports -------------------------------------------
from fastapi import APIRouter
from pydantic import BaseModel


# Constants / Variables -------------------------------------------
router = APIRouter(
    prefix="/api",
    tags=["REST"],
)


# Classes -------------------------------------------
class OfferRequest(BaseModel):
    """The applicant and annual salary used to create a mock offer."""

    applicant_id: str
    salary: float


class OfferResponse(BaseModel):
    """The mock offer details returned after the candidate accepts it."""

    applicant_id: str
    offered_salary: float
    candidate_response: str

@router.post(
    "/offers",
    response_model=OfferResponse,
)
def extend_offer(offer: OfferRequest):
    """Create a mock accepted offer from the supplied applicant and salary."""
    candidate_response = (
        f"Thank you so much for the offer! I'm extremely excited about "
        f"the opportunity. I would be very happy to accept the "
        f"${offer.salary:,.0f} offer and I'm looking forward to joining the team."
    )

    return OfferResponse(
        applicant_id=offer.applicant_id,
        offered_salary=offer.salary,
        candidate_response=candidate_response,
    )
