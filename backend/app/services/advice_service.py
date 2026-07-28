from app.schemas.clinical import AdviceRequest, AdviceResponse


def generate_advice(request: AdviceRequest) -> AdviceResponse:
    if not request.interactions:
        raise ValueError("No interactions provided")

    max_severity = request.interactions[0].severity
    is_high_risk = max_severity in {"contraindicated", "major"}
    uses_heuristic_evidence = any(
        interaction.source_type == "heuristic" for interaction in request.interactions
    )

    action_plan = [
        "Review the interacting medications before dispensing or prescribing.",
        "Discuss risk-benefit and available alternatives with the clinical team.",
    ]

    if is_high_risk:
        action_plan.append("Use human sign-off before finalizing the plan.")

    if uses_heuristic_evidence:
        action_plan.append(
            "Treat this as provisional until a live interaction source is confirmed by pharmacist or physician review."
        )

    summary = "This interaction should be reviewed before any final medication decision is made."
    if uses_heuristic_evidence:
        summary = "Provisional interaction finding: verify with clinician review and trusted references before final action."

    disclaimer = "Assistive output only. Final decision by licensed clinician."
    if uses_heuristic_evidence:
        disclaimer += " Includes heuristic fallback evidence and requires human validation."

    return AdviceResponse(
        summary=summary,
        action_plan=action_plan,
        alternatives=["Consider a non-NSAID pain option if clinically appropriate."] if is_high_risk else [],
        red_flags=["Worsening bruising", "Black stools", "Unexplained bleeding"] if is_high_risk else [],
        citations=[interaction.source for interaction in request.interactions],
        disclaimer=disclaimer,
    )
