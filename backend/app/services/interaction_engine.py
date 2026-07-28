import json
import os
from pathlib import Path

from app.schemas.clinical import InteractionCheckRequest, InteractionCheckResponse, InteractionItem

from app.services.dailymed_client import get_label_snippet
from app.services.external_interactions_client import is_external_provider_enabled, lookup_external_interactions
from app.services.openfda_client import get_safety_note
from app.services.rxnav_client import get_rxnorm_name, lookup_interactions, lookup_rxcui, normalize_medication_name, summarize_drug_pair


DEFAULT_HEURISTIC_INTERACTION_RULES = [
    {
        "drug_a": "Warfarin",
        "drug_b": "Ibuprofen",
        "keywords_a": ["warfarin"],
        "keywords_b": ["ibuprofen", "advil", "motrin"],
        "severity": "major",
        "mechanism": "Combined anticoagulant and NSAID effects increase bleeding risk.",
        "clinical_effect": "Higher likelihood of gastrointestinal or systemic bleeding.",
        "recommendation": "Review necessity, consider alternatives, and monitor for bleeding signs.",
        "monitoring": ["Monitor for bruising", "Check stool for blood", "Review INR if applicable"],
    },
    {
        "drug_a": "Warfarin",
        "drug_b": "Ginkgo Biloba",
        "keywords_a": ["warfarin"],
        "keywords_b": ["ginkgo", "ginko"],
        "severity": "major",
        "mechanism": "Concurrent anticoagulant and antiplatelet effects may increase bleeding risk.",
        "clinical_effect": "Higher likelihood of bruising, mucosal bleeding, or serious hemorrhage.",
        "recommendation": "Avoid or closely monitor this combination and document clinical rationale.",
        "monitoring": ["Monitor for bruising", "Check for bleeding symptoms", "Review INR if applicable"],
    },
    {
        "drug_a": "Warfarin",
        "drug_b": "Aspirin",
        "keywords_a": ["warfarin"],
        "keywords_b": ["aspirin", "acetylsalicylic"],
        "severity": "major",
        "mechanism": "Dual anticoagulant and antiplatelet effects increase bleeding potential.",
        "clinical_effect": "Elevated risk of major bleeding events.",
        "recommendation": "Use only with clear indication and close monitoring.",
        "monitoring": ["Monitor for bleeding", "Review INR trend", "Review GI risk"],
    },
    {
        "drug_a": "Warfarin",
        "drug_b": "Alcohol",
        "keywords_a": ["warfarin"],
        "keywords_b": ["alcohol", "ethanol", "beer", "wine", "whiskey", "vodka"],
        "severity": "major",
        "mechanism": "Alcohol intake can alter warfarin metabolism and increase anticoagulant effect variability.",
        "clinical_effect": "Increased risk of elevated INR and bleeding, especially with heavy or irregular alcohol use.",
        "recommendation": "Avoid heavy alcohol use and monitor INR/bleeding risk closely when alcohol exposure is present.",
        "monitoring": ["Monitor INR trend", "Assess for bleeding symptoms", "Counsel on alcohol intake consistency"],
    },
    {
        "drug_a": "Simvastatin",
        "drug_b": "Clarithromycin",
        "keywords_a": ["simvastatin"],
        "keywords_b": ["clarithromycin", "biaxin"],
        "severity": "major",
        "mechanism": "CYP3A4 inhibition can increase simvastatin concentration.",
        "clinical_effect": "Increased risk of myopathy or rhabdomyolysis.",
        "recommendation": "Avoid co-administration or hold simvastatin while clarithromycin is used.",
        "monitoring": ["Monitor for muscle pain", "Check CK if symptomatic"],
    },
    {
        "drug_a": "Sildenafil",
        "drug_b": "Nitroglycerin",
        "keywords_a": ["sildenafil", "viagra"],
        "keywords_b": ["nitroglycerin", "isosorbide"],
        "severity": "contraindicated",
        "mechanism": "Additive vasodilatory effects can cause profound hypotension.",
        "clinical_effect": "Risk of severe hypotension, syncope, or ischemic events.",
        "recommendation": "Do not co-administer; this combination is contraindicated.",
        "monitoring": ["Urgent clinical review required"],
    },
]


def _load_heuristic_rules() -> list[dict]:
    default_rules = DEFAULT_HEURISTIC_INTERACTION_RULES
    default_path = Path(__file__).resolve().parent.parent / "data" / "interaction_rules.json"
    configured_path = os.getenv("HEURISTIC_RULES_FILE", "").strip()
    rules_path = Path(configured_path) if configured_path else default_path

    try:
        payload = json.loads(rules_path.read_text(encoding="utf-8"))
    except Exception:
        return default_rules

    if not isinstance(payload, list):
        return default_rules

    required_fields = {
        "drug_a",
        "drug_b",
        "keywords_a",
        "keywords_b",
        "severity",
        "mechanism",
        "clinical_effect",
        "recommendation",
        "monitoring",
    }
    valid_severity = {"contraindicated", "major", "moderate", "minor", "none"}

    normalized_rules: list[dict] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        if not required_fields.issubset(item.keys()):
            continue
        if item.get("severity") not in valid_severity:
            continue
        if not isinstance(item.get("keywords_a"), list) or not isinstance(item.get("keywords_b"), list):
            continue
        if not isinstance(item.get("monitoring"), list):
            continue
        normalized_rules.append(item)

    return normalized_rules or default_rules


HEURISTIC_INTERACTION_RULES = _load_heuristic_rules()


def _contains_keyword(names: set[str], keywords: list[str]) -> bool:
    return any(any(keyword in name for keyword in keywords) for name in names)


def _max_severity(interactions: list[InteractionItem]) -> str:
    rank = {
        "none": 0,
        "minor": 1,
        "moderate": 2,
        "major": 3,
        "contraindicated": 4,
    }
    return max(interactions, key=lambda item: rank.get(item.severity, 0)).severity


def _build_external_items(items: list[dict]) -> list[InteractionItem]:
    interaction_items: list[InteractionItem] = []
    for item in items[:20]:
        interaction_items.append(
            InteractionItem(
                drug_a=item["drug_a"],
                drug_b=item["drug_b"],
                severity=item["severity"],
                source_type="external_api",
                mechanism=item["mechanism"],
                clinical_effect=item["clinical_effect"],
                recommendation=item["recommendation"],
                monitoring=item["monitoring"],
                source=f"External provider | {item['source']}",
            )
        )
    return interaction_items


def check_interactions(request: InteractionCheckRequest) -> InteractionCheckResponse:
    cleaned_names = [
        medication.name_entered.strip()
        for medication in request.medications
        if medication.name_entered.strip()
    ]

    provider_mode = os.getenv("INTERACTION_PROVIDER", "auto").strip().lower()

    if provider_mode in {"external", "auto"} and is_external_provider_enabled():
        external_items = lookup_external_interactions(cleaned_names)
        if external_items:
            interactions = _build_external_items(external_items)
            return InteractionCheckResponse(
                max_severity=_max_severity(interactions),
                interactions=interactions,
                requires_clinician_review=True,
            )

    if provider_mode in {"rxnav", "auto"}:
        try:
            matches = [lookup_rxcui(name) for name in cleaned_names]
            resolved_matches = [match for match in matches if match is not None]
            rxcuis = [match.rxcui for match in resolved_matches]
            interactions = lookup_interactions(rxcuis)

            if interactions:
                interaction_items = []
                for interaction in interactions[:10]:
                    description = interaction.get("description") or "Potential interaction detected by RxNav."
                    pair = interaction.get("interactionConceptPair", [{}])[0]
                    concept_a = pair.get("interactionConcept", [{}])[0].get("name", cleaned_names[0] if cleaned_names else "Unknown")
                    concept_b = pair.get("interactionConcept", [{}, {}])[1].get("name", cleaned_names[1] if len(cleaned_names) > 1 else "Unknown")
                    resolved_a = get_rxnorm_name(resolved_matches[0].rxcui) if resolved_matches else None
                    resolved_b = get_rxnorm_name(resolved_matches[1].rxcui) if len(resolved_matches) > 1 else None
                    interaction_items.append(
                        InteractionItem(
                            drug_a=resolved_a or concept_a,
                            drug_b=resolved_b or concept_b,
                            severity="major",
                            source_type="live_rxcui",
                            mechanism=description,
                            clinical_effect="Clinical significance determined by RxNav interaction data.",
                            recommendation="Review with clinician before dispensing or prescribing.",
                            monitoring=["Monitor closely", "Confirm therapeutic necessity"],
                            source=f"Live RxNorm lookup ({', '.join(rxcuis)}) | {get_label_snippet(concept_a)} | {get_safety_note(concept_b)}",
                        )
                    )

                return InteractionCheckResponse(
                    max_severity="major",
                    interactions=interaction_items,
                    requires_clinician_review=True,
                )
        except Exception:
            pass

    normalized_names = {normalize_medication_name(medication) for medication in request.medications if medication.name_entered.strip()}

    for rule in HEURISTIC_INTERACTION_RULES:
        matches_direct = _contains_keyword(normalized_names, rule["keywords_a"]) and _contains_keyword(normalized_names, rule["keywords_b"])
        matches_reverse = _contains_keyword(normalized_names, rule["keywords_b"]) and _contains_keyword(normalized_names, rule["keywords_a"])
        if not (matches_direct or matches_reverse):
            continue

        pair = summarize_drug_pair(rule["drug_a"], rule["drug_b"])
        return InteractionCheckResponse(
            max_severity=rule["severity"],
            interactions=[
                InteractionItem(
                    drug_a=pair["drug_a"],
                    drug_b=pair["drug_b"],
                    severity=rule["severity"],
                    source_type="heuristic",
                    mechanism=rule["mechanism"],
                    clinical_effect=rule["clinical_effect"],
                    recommendation=rule["recommendation"],
                    monitoring=rule["monitoring"],
                    source=f"Fallback heuristic | {pair['source']} | {get_label_snippet(rule['drug_a'])} | {get_safety_note(rule['drug_b'])}",
                )
            ],
            requires_clinician_review=True,
        )

    return InteractionCheckResponse(max_severity="none", interactions=[], requires_clinician_review=False)

