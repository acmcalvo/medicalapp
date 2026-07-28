from fastapi import APIRouter


router = APIRouter()


@router.post("/normalize")
async def normalize_medications(payload: dict) -> dict:
    return {"normalized": [], "unresolved": payload.get("medications", [])}
