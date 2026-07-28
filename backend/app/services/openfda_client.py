from __future__ import annotations

from typing import Any

import httpx


_OPENFDA_BASE_URL = "https://api.fda.gov/drug/label.json"


def _request_json(params: dict[str, str]) -> dict[str, Any]:
    response = httpx.get(_OPENFDA_BASE_URL, params=params, timeout=10.0)
    response.raise_for_status()
    return response.json()


def get_safety_note(drug_name: str) -> str:
    try:
        payload = _request_json({"search": f'openfda.brand_name:"{drug_name}"', "limit": "1"})
        results = payload.get("results", [])
        if not results:
            return f"openFDA safety information not found for {drug_name}."

        warnings = results[0].get("warnings_and_precautions", [])
        if warnings:
            return f"openFDA safety note: {warnings[0][:180]}"

        return f"openFDA safety information found for {drug_name}."
    except Exception:
        return f"openFDA safety information unavailable for {drug_name}."
