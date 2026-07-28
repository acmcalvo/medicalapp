from __future__ import annotations

from typing import Any

import httpx


_DAILYMED_BASE_URL = "https://dailymed.nlm.nih.gov/dailymed/services/v2"


def _request_json(path: str, params: dict[str, str] | None = None) -> dict[str, Any]:
    response = httpx.get(f"{_DAILYMED_BASE_URL}{path}", params=params, timeout=10.0)
    response.raise_for_status()
    return response.json()


def get_label_snippet(drug_name: str) -> str:
    try:
        payload = _request_json("/spls.json", params={"drug_name": drug_name, "limit": "1"})
        spls = payload.get("data", [])
        if not spls:
            return f"DailyMed label not found for {drug_name}."

        label = spls[0]
        title = label.get("title") or drug_name
        set_id = label.get("setid") or "unknown"
        return f"DailyMed label: {title} (setid: {set_id})"
    except Exception:
        return f"DailyMed label unavailable for {drug_name}."
