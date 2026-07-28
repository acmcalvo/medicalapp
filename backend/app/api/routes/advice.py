from fastapi import APIRouter, HTTPException

from app.schemas.clinical import AdviceRequest, AdviceResponse

from app.services.advice_service import generate_advice as generate_advice_service


router = APIRouter()


@router.post("/generate", response_model=AdviceResponse)
async def generate_advice(request: AdviceRequest) -> AdviceResponse:
    if not request.interactions:
        raise HTTPException(status_code=400, detail="No interactions provided")

    return generate_advice_service(request)
