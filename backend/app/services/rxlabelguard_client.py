from __future__ import annotations

from typing import Any

import httpx

from app.core.config import settings

def _request_json(params: dict[str, str]) -> dict[str, Any]:
    if not settings.rxlabelguard_base_url:
        raise RuntimeError("RxLabelGuard base URL is not configured")

    headers: dict[str, str] = {}
    if settings.rxlabelguard_api_key:
        if settings.rxlabelguard_api_key_header.lower() == "authorization":
            headers[settings.rxlabelguard_api_key_header] = (
                f"{settings.rxlabelguard_api_key_prefix} {settings.rxlabelguard_api_key}".strip()
            )
        else:
            headers[settings.rxlabelguard_api_key_header] = settings.rxlabelguard_api_key

    response = httpx.get(
        f"{settings.rxlabelguard_base_url}{settings.rxlabelguard_query_path}",
        params=params,
        headers=headers or None,
        timeout=10.0,
    )
    response.raise_for_status()
    return response.json()


def get_label_guard_note(drug_name: str) -> str:
    try:
        payload = _request_json({"drug_name": drug_name, "limit": "1"})
        results = payload.get("results", payload.get("data", []))
        if not results:
            return f"RxLabelGuard label not found for {drug_name}."

        label = results[0]
        title = label.get("title") or label.get("label") or drug_name
        identifier = label.get("id") or label.get("setid") or label.get("label_id") or "unknown"
        return f"RxLabelGuard label: {title} (id: {identifier})"
    except Exception:
        return f"RxLabelGuard label unavailable for {drug_name}."