from fastapi import APIRouter

from app.schemas.clinical import InteractionCheckRequest, InteractionCheckResponse

from app.services.interaction_engine import check_interactions as check_interactions_service


router = APIRouter()


@router.post("/check", response_model=InteractionCheckResponse)
async def check_interactions(request: InteractionCheckRequest) -> InteractionCheckResponse:
    return check_interactions_service(request)
