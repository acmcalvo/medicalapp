from app.schemas.clinical import AdviceRequest, AdviceResponse


CONDITION_RECOMMENDATIONS = [
    {
        "condition_keywords": ["diabetes", "diabetic", "type 1 diabetes", "type 2 diabetes"],
        "recommendation": (
            "Diabetes can raise the importance of glucose-sensitive medicines; monitor blood sugar closely "
            "when corticosteroids or fluoroquinolones are used and coordinate diabetes medication adjustments if needed."
        ),
    },
    {
        "condition_keywords": ["hypertension", "high blood pressure"],
        "recommendation": (
            "Hypertension can make blood-pressure effects more important; monitor blood pressure and review medicines "
            "that may raise sodium retention, fluid balance concerns, or cardiovascular risk."
        ),
    },
    {
        "condition_keywords": ["kidney disease", "chronic kidney disease", "ckd", "renal impairment"],
        "recommendation": (
            "Kidney disease can change how medicines are cleared; review renal dosing, avoid nephrotoxic combinations "
            "when possible, and monitor kidney function when treatment carries renal risk."
        ),
    },
    {
        "condition_keywords": ["liver disease", "hepatic impairment", "cirrhosis", "hepatitis"],
        "recommendation": (
            "Liver disease can alter drug metabolism; consider dose adjustments, check for hepatotoxic medicines, "
            "and monitor liver-related adverse effects more closely."
        ),
    },
    {
        "condition_keywords": ["lung cancer", "pulmonary cancer"],
        "recommendation": (
            "Lung cancer can increase pulmonary vulnerability; review respiratory status, watch for cough or dyspnea, "
            "and coordinate oncology follow-up when a medicine carries lung toxicity risk."
        ),
    },
    {
        "condition_keywords": ["copd", "asthma", "chronic obstructive pulmonary disease"],
        "recommendation": (
            "Chronic lung disease can increase the impact of respiratory side effects; monitor breathing symptoms and "
            "avoid medicines that could worsen respiratory status when alternatives exist."
        ),
    },
    {
        "condition_keywords": ["pregnant", "pregnancy"],
        "recommendation": (
            "Pregnancy can change the risk-benefit balance; review fetal safety, coordinate obstetric input when needed, "
            "and prefer medicines with established pregnancy safety data when possible."
        ),
    },
]


def _matches_condition(condition_text: str, keywords: list[str]) -> bool:
    normalized_condition = condition_text.strip().lower()
    return any(keyword in normalized_condition for keyword in keywords)


def _build_condition_recommendations(conditions: list[str]) -> list[str]:
    recommendations: list[str] = []
    seen: set[str] = set()

    for condition in conditions:
        for rule in CONDITION_RECOMMENDATIONS:
            if _matches_condition(condition, rule["condition_keywords"]):
                recommendation = rule["recommendation"]
                if recommendation in seen:
                    continue
                seen.add(recommendation)
                recommendations.append(recommendation)

    return recommendations


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

    condition_recommendations = _build_condition_recommendations(request.patient.conditions)
    action_plan.extend(condition_recommendations)

    if is_high_risk:
        action_plan.append("Use human sign-off before finalizing the plan.")

    if uses_heuristic_evidence:
        action_plan.append(
            "Treat this as provisional until a live interaction source is confirmed by pharmacist or physician review."
        )

    summary = "This interaction should be reviewed before any final medication decision is made."
    if condition_recommendations:
        summary = "Diagnosis-aware review: this interaction and the patient conditions should both be considered before final action."
    if uses_heuristic_evidence:
        summary = "Provisional interaction finding: verify with clinician review and trusted references before final action."
        if condition_recommendations:
            summary = (
                "Provisional diagnosis-aware finding: verify with clinician review, the patient conditions, "
                "and trusted references before final action."
            )

    disclaimer = "Assistive output only. Final decision by licensed clinician."
    if uses_heuristic_evidence:
        disclaimer += " Includes heuristic fallback evidence and requires human validation."
    if condition_recommendations:
        disclaimer += " Includes diagnosis-specific guidance based on the provided conditions."

    return AdviceResponse(
        summary=summary,
        action_plan=action_plan,
        alternatives=["Consider a non-NSAID pain option if clinically appropriate."] if is_high_risk else [],
        red_flags=["Worsening bruising", "Black stools", "Unexplained bleeding"] if is_high_risk else [],
        citations=[interaction.source for interaction in request.interactions],
        disclaimer=disclaimer,
    )
