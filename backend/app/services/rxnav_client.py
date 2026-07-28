from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from app.schemas.clinical import MedicationInput


@dataclass(frozen=True)
class RxNormMatch:
    rxcui: str
    name: str
    score: float


_RXNAV_BASE_URL = "https://rxnav.nlm.nih.gov/REST"


def _request_json(path: str, params: dict[str, str] | None = None) -> dict[str, Any]:
    response = httpx.get(f"{_RXNAV_BASE_URL}{path}", params=params, timeout=10.0)
    response.raise_for_status()
    return response.json()


def normalize_medication_name(medication: MedicationInput) -> str:
    return medication.name_entered.strip().lower()


def approximate_match(drug_name: str) -> RxNormMatch | None:
    payload = _request_json(
        "/approximateTerm.json",
        params={"term": drug_name, "maxEntries": "1"},
    )
    candidates = payload.get("approximateGroup", {}).get("candidate", [])
    if not candidates:
        return None

    candidate = candidates[0]
    score = float(candidate.get("score", 0))
    rxcui = str(candidate.get("rxcui", ""))
    if not rxcui:
        return None

    name = candidate.get("name") or drug_name
    return RxNormMatch(rxcui=rxcui, name=name, score=score)


def lookup_rxcui(drug_name: str) -> RxNormMatch | None:
    match = approximate_match(drug_name)
    if match:
        return match

    payload = _request_json("/rxcui.json", params={"name": drug_name})
    rxcui = payload.get("idGroup", {}).get("rxnormId", [])
    if not rxcui:
        return None

    return RxNormMatch(rxcui=str(rxcui[0]), name=drug_name, score=100.0)


def get_rxnorm_name(rxcui: str) -> str | None:
    payload = _request_json(f"/rxcui/{rxcui}.json")
    return payload.get("idGroup", {}).get("name")


def lookup_interactions(rxcuis: list[str]) -> list[dict[str, Any]]:
    if not rxcuis:
        return []

    payload = _request_json("/interaction/list.json", params={"rxcuis": "+".join(rxcuis)})
    groups = payload.get("fullInteractionTypeGroup", [])
    interactions: list[dict[str, Any]] = []

    for group in groups:
        for full_type in group.get("fullInteractionType", []):
            for interaction_pair in full_type.get("interactionPair", []):
                interactions.append(interaction_pair)

    return interactions


def summarize_drug_pair(drug_a: str, drug_b: str) -> dict[str, str]:
    return {
        "drug_a": drug_a,
        "drug_b": drug_b,
        "source": "Normalized pair from fallback rule",
    }
