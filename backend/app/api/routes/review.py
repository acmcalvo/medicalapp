from fastapi import APIRouter, HTTPException
from datetime import datetime, timezone
from uuid import uuid4


router = APIRouter()


@router.post("/review-signoff")
async def review_signoff(payload: dict) -> dict:
    case_id = payload.get("case_id") or f"case-{uuid4().hex[:8]}"
    status = payload.get("status", "signed_off")
    note = (payload.get("note") or "").strip()
    uses_fallback_evidence = bool(payload.get("uses_fallback_evidence"))

    if status == "signed_off" and uses_fallback_evidence and not note:
        raise HTTPException(
            status_code=400,
            detail="Reviewer note is required before approving a case that includes fallback heuristic evidence.",
        )

    reviewed_at = datetime.now(timezone.utc).isoformat()

    return {
        "status": status,
        "case_id": case_id,
        "reviewed_at": reviewed_at,
        "payload": payload,
    }


@router.get("/audit/{case_id}")
async def get_audit_case(case_id: str) -> dict:
    reviewed_at = datetime.now(timezone.utc).isoformat()
    return {
        "case_id": case_id,
        "events": [
            {
                "timestamp": reviewed_at,
                "event_type": "case_reviewed",
                "detail": "Audit history is currently generated from the latest case activity.",
            }
        ],
    }
