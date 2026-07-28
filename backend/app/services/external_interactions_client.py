from __future__ import annotations

import os
from typing import Any

import httpx


def is_external_provider_enabled() -> bool:
    return bool(os.getenv("INTERACTIONS_API_URL"))


def _extract_interaction_list(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]

    if not isinstance(payload, dict):
        return []

    candidates = [
        payload.get("interactions"),
        payload.get("results"),
        payload.get("data", {}).get("interactions") if isinstance(payload.get("data"), dict) else None,
    ]

    for candidate in candidates:
        if isinstance(candidate, list):
            return [item for item in candidate if isinstance(item, dict)]

    return []


def _coerce_severity(value: Any) -> str:
    severity = str(value or "major").strip().lower()
    valid = {"contraindicated", "major", "moderate", "minor", "none"}
    return severity if severity in valid else "major"


def _to_string(value: Any, default: str) -> str:
    text = str(value or "").strip()
    return text if text else default


def lookup_external_interactions(medication_names: list[str]) -> list[dict[str, Any]]:
    if not medication_names:
        return []

    api_url = os.getenv("INTERACTIONS_API_URL", "").strip()
    if not api_url:
        return []

    api_key = os.getenv("INTERACTIONS_API_KEY", "").strip()
    auth_header = os.getenv("INTERACTIONS_API_AUTH_HEADER", "Authorization").strip() or "Authorization"
    timeout = float(os.getenv("INTERACTIONS_API_TIMEOUT_SEC", "10"))

    headers: dict[str, str] = {"Content-Type": "application/json"}
    if api_key:
        headers[auth_header] = f"Bearer {api_key}"

    # Send both keys so common provider shapes work without custom code.
    payload = {
        "drugs": medication_names,
        "medications": medication_names,
    }

    try:
        response = httpx.post(api_url, headers=headers, json=payload, timeout=timeout)
        response.raise_for_status()
        raw_items = _extract_interaction_list(response.json())
    except Exception:
        return []

    mapped_items: list[dict[str, Any]] = []
    for item in raw_items:
        evidence = item.get("evidence") if isinstance(item.get("evidence"), dict) else {}
        evidence_source = item.get("source") or evidence.get("source")
        spl_set_id = evidence.get("spl_set_id")
        source_text = _to_string(evidence_source, "External interaction provider")
        if spl_set_id:
            source_text = f"{source_text} (SPL Set ID: {spl_set_id})"

        drug_a = _to_string(
            item.get("drug_a")
            or item.get("drugA")
            or item.get("medication1")
            or item.get("drug1"),
            "Unknown drug",
        )
        drug_b = _to_string(
            item.get("drug_b")
            or item.get("drugB")
            or item.get("medication2")
            or item.get("drug2"),
            "Unknown drug",
        )

        mapped_items.append(
            {
                "drug_a": drug_a,
                "drug_b": drug_b,
                "severity": _coerce_severity(item.get("severity")),
                "mechanism": _to_string(item.get("mechanism"), "Potential interaction detected by external provider."),
                "clinical_effect": _to_string(item.get("clinical_effect") or item.get("clinicalEffect"), "Clinical significance requires review."),
                "recommendation": _to_string(item.get("recommendation"), "Review with clinician before dispensing or prescribing."),
                "monitoring": item.get("monitoring") if isinstance(item.get("monitoring"), list) else ["Monitor clinically as appropriate"],
                "source": source_text,
            }
        )

    return mapped_items
