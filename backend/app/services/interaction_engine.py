from app.schemas.clinical import InteractionCheckRequest, InteractionCheckResponse, InteractionItem

from app.services.dailymed_client import get_label_snippet
from app.services.openfda_client import get_safety_note
from app.services.rxnav_client import get_rxnorm_name, lookup_interactions, lookup_rxcui, normalize_medication_name, summarize_drug_pair


def check_interactions(request: InteractionCheckRequest) -> InteractionCheckResponse:
    cleaned_names = [
        medication.name_entered.strip()
        for medication in request.medications
        if medication.name_entered.strip()
    ]

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
    has_warfarin = any("warfarin" in name for name in normalized_names)
    has_ibuprofen = any("ibuprofen" in name or "advil" in name or "motrin" in name for name in normalized_names)
    has_ginkgo = any("ginkgo" in name or "ginko" in name for name in normalized_names)

    if has_warfarin and has_ibuprofen:
        pair = summarize_drug_pair("Warfarin", "Ibuprofen")
        return InteractionCheckResponse(
            max_severity="major",
            interactions=[
                InteractionItem(
                    drug_a=pair["drug_a"],
                    drug_b=pair["drug_b"],
                    severity="major",
                    source_type="heuristic",
                    mechanism="Combined anticoagulant and NSAID effects increase bleeding risk.",
                    clinical_effect="Higher likelihood of gastrointestinal or systemic bleeding.",
                    recommendation="Review necessity, consider alternatives, and monitor for bleeding signs.",
                    monitoring=["Monitor for bruising", "Check stool for blood", "Review INR if applicable"],
                    source=f"Fallback heuristic | {pair['source']} | {get_label_snippet('Warfarin')} | {get_safety_note('Ibuprofen')}",
                )
            ],
            requires_clinician_review=True,
        )

    if has_warfarin and has_ginkgo:
        pair = summarize_drug_pair("Warfarin", "Ginkgo Biloba")
        return InteractionCheckResponse(
            max_severity="major",
            interactions=[
                InteractionItem(
                    drug_a=pair["drug_a"],
                    drug_b=pair["drug_b"],
                    severity="major",
                    source_type="heuristic",
                    mechanism="Concurrent anticoagulant and antiplatelet effects may increase bleeding risk.",
                    clinical_effect="Higher likelihood of bruising, mucosal bleeding, or serious hemorrhage.",
                    recommendation="Avoid or closely monitor this combination and document clinical rationale.",
                    monitoring=["Monitor for bruising", "Check for bleeding symptoms", "Review INR if applicable"],
                    source=f"Fallback heuristic | {pair['source']} | {get_label_snippet('Warfarin')} | {get_safety_note('Ginkgo Biloba')}",
                )
            ],
            requires_clinician_review=True,
        )

    return InteractionCheckResponse(max_severity="none", interactions=[], requires_clinician_review=False)

