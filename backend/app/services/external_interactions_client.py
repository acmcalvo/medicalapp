from __future__ import annotations

import ast
import json
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
        payload.get("drug_interactions"),
        payload.get("pairwise"),
        payload.get("results"),
        payload.get("data", {}).get("interactions") if isinstance(payload.get("data"), dict) else None,
        payload.get("data", {}).get("results") if isinstance(payload.get("data"), dict) else None,
        payload.get("data", {}).get("drug_interactions") if isinstance(payload.get("data"), dict) else None,
    ]

    for candidate in candidates:
        if isinstance(candidate, list):
            return [item for item in candidate if isinstance(item, dict)]
        if isinstance(candidate, dict):
            return [candidate]

    if any(key in payload for key in ("drug_a", "drugA", "medication1", "drug1")):
        return [payload]

    return []


def _coerce_severity(value: Any) -> str:
    severity = str(value or "moderate").strip().lower()
    valid = {"contraindicated", "major", "moderate", "minor", "none"}
    return severity if severity in valid else "major"


def _to_string(value: Any, default: str) -> str:
    text = str(value or "").strip()
    return text if text else default


def _parse_mapping_like(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value

    if not isinstance(value, str):
        return {}

    text = value.strip()
    if not text:
        return {}

    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
    except Exception:
        pass

    try:
        parsed = ast.literal_eval(text)
        if isinstance(parsed, dict):
            return parsed
    except Exception:
        pass

    return {}


def _infer_severity_from_text(value: str) -> str | None:
    lowered = value.lower()
    for severity in ("contraindicated", "major", "moderate", "minor", "none"):
        if severity in lowered:
            return severity
    return None


def _build_monitoring(value: Any) -> list[str]:
    if isinstance(value, list):
        normalized = [str(item).strip() for item in value if str(item).strip()]
        if normalized:
            return normalized

    if isinstance(value, str) and value.strip():
        return [value.strip()]

    return ["Monitor clinically as appropriate"]


def _map_external_item(item: dict[str, Any]) -> dict[str, Any]:
    interaction_block = _parse_mapping_like(item.get("interaction"))
    details_block = _parse_mapping_like(item.get("details"))
    mechanism_block = _parse_mapping_like(item.get("mechanism"))
    evidence = item.get("evidence") if isinstance(item.get("evidence"), dict) else {}

    evidence_source = item.get("source") or evidence.get("source") or interaction_block.get("source")
    source_text = _to_string(evidence_source, "External interaction provider")

    spl_set_id = (
        evidence.get("spl_set_id")
        or interaction_block.get("spl_set_id")
        or interaction_block.get("setid")
        or details_block.get("spl_set_id")
    )
    if spl_set_id:
        source_text = f"{source_text} (SPL Set ID: {spl_set_id})"

    drug_a = _to_string(
        item.get("drug_a")
        or item.get("drugA")
        or item.get("medication1")
        or item.get("drug1")
        or interaction_block.get("drug_a")
        or interaction_block.get("drug1"),
        "Unknown drug",
    )
    drug_b = _to_string(
        item.get("drug_b")
        or item.get("drugB")
        or item.get("medication2")
        or item.get("drug2")
        or interaction_block.get("drug_b")
        or interaction_block.get("drug2"),
        "Unknown drug",
    )

    raw_description = (
        item.get("mechanism")
        or item.get("description")
        or item.get("summary")
        or interaction_block.get("description")
        or mechanism_block.get("description")
        or details_block.get("description")
    )
    mechanism = _to_string(raw_description, "Potential interaction detected by external provider.")

    clinical_effect = _to_string(
        item.get("clinical_effect")
        or item.get("clinicalEffect")
        or interaction_block.get("clinical_effect")
        or interaction_block.get("effect")
        or details_block.get("clinical_effect"),
        "Clinical significance requires review.",
    )

    recommendation = _to_string(
        item.get("recommendation")
        or item.get("action")
        or interaction_block.get("recommendation")
        or details_block.get("recommendation"),
        "Review with clinician before dispensing or prescribing.",
    )

    severity = _coerce_severity(
        item.get("severity")
        or item.get("risk_level")
        or interaction_block.get("severity")
        or details_block.get("severity")
    )
    inferred = _infer_severity_from_text(mechanism)
    if inferred:
        severity = _coerce_severity(inferred)

    monitoring = _build_monitoring(
        item.get("monitoring")
        or interaction_block.get("monitoring")
        or details_block.get("monitoring")
    )

    return {
        "drug_a": drug_a,
        "drug_b": drug_b,
        "severity": severity,
        "mechanism": mechanism,
        "clinical_effect": clinical_effect,
        "recommendation": recommendation,
        "monitoring": monitoring,
        "source": source_text,
    }


def lookup_external_interactions(medication_names: list[str]) -> list[dict[str, Any]]:
    if not medication_names:
        return []

    api_url = os.getenv("INTERACTIONS_API_URL", "").strip()
    if not api_url:
        return []

    api_key = os.getenv("INTERACTIONS_API_KEY", "").strip()
    auth_header = os.getenv("INTERACTIONS_API_AUTH_HEADER", "Authorization").strip() or "Authorization"
    auth_prefix = os.getenv("INTERACTIONS_API_AUTH_PREFIX", "Bearer").strip()
    timeout = float(os.getenv("INTERACTIONS_API_TIMEOUT_SEC", "10"))

    headers: dict[str, str] = {"Content-Type": "application/json"}
    if api_key:
        if auth_header.lower() == "authorization":
            headers[auth_header] = f"{auth_prefix} {api_key}".strip()
        else:
            headers[auth_header] = api_key

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
        if not isinstance(item, dict):
            continue
        mapped_items.append(_map_external_item(item))

    return mapped_items
