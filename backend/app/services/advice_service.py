from app.schemas.clinical import AdviceRequest, AdviceResponse, InteractionItem


DEFAULT_SUMMARY_QUESTION = "Summarize the medication review for clinician sign-off."
SEVERITY_RANK = {
    "none": 0,
    "minor": 1,
    "moderate": 2,
    "major": 3,
    "contraindicated": 4,
}


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


def _dedupe_strings(items: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []

    for item in items:
        normalized_item = item.strip()
        if not normalized_item:
            continue
        lowered = normalized_item.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        deduped.append(normalized_item)

    return deduped


def _max_severity(interactions: list[InteractionItem]) -> str:
    return max(interactions, key=lambda interaction: SEVERITY_RANK.get(interaction.severity, 0)).severity


def _question_text(question: str | None) -> str:
    return (question or "").strip().lower()


def _is_follow_up_question(question: str | None) -> bool:
    normalized_question = _question_text(question)
    return bool(normalized_question) and normalized_question != DEFAULT_SUMMARY_QUESTION.lower()


def _matched_conditions(conditions: list[str]) -> list[str]:
    matched: list[str] = []

    for condition in conditions:
        for rule in CONDITION_RECOMMENDATIONS:
            if _matches_condition(condition, rule["condition_keywords"]):
                matched.append(condition.strip())
                break

    return _dedupe_strings(matched)


def _collect_monitoring_points(interactions: list[InteractionItem]) -> list[str]:
    monitoring_points: list[str] = []
    for interaction in interactions:
        monitoring_points.extend(interaction.monitoring)
    return _dedupe_strings(monitoring_points)


def _build_follow_up_response(
    request: AdviceRequest,
    condition_recommendations: list[str],
    is_high_risk: bool,
) -> tuple[str, list[str], list[str], list[str]]:
    question = _question_text(request.question)
    primary_interaction = max(
        request.interactions,
        key=lambda interaction: SEVERITY_RANK.get(interaction.severity, 0),
    )
    matched_conditions = _matched_conditions(request.patient.conditions)
    monitoring_points = _collect_monitoring_points(request.interactions)
    condition_phrase = ", ".join(matched_conditions) if matched_conditions else "the reported conditions"
    explanation_points = _dedupe_strings(
        [
            primary_interaction.clinical_effect,
            primary_interaction.recommendation,
            *condition_recommendations,
        ]
    )

    if any(keyword in question for keyword in ["why", "risk", "explain", "because", "interaction"]):
        summary = (
            f"Follow-up answer: {primary_interaction.drug_a} with {primary_interaction.drug_b} is flagged as "
            f"{primary_interaction.severity} because {primary_interaction.mechanism.lower()}"
        )
        if matched_conditions:
            summary += f". {condition_phrase.capitalize()} adds extra review context for this case."
        action_plan = explanation_points[:4]
        return summary, action_plan, [], []

    if any(keyword in question for keyword in ["monitor", "watch", "red flag", "symptom", "sign"]):
        summary = (
            "Follow-up answer: monitor for the interaction-specific safety signals below"
            if monitoring_points
            else "Follow-up answer: no extra monitoring points were derived beyond the current recommendation."
        )
        action_plan = monitoring_points[:5] or explanation_points[:3]
        red_flags = [
            "Escalate urgently if bleeding, black stools, syncope, or other acute decline appears."
        ] if is_high_risk else []
        return summary, action_plan, [], red_flags

    if any(keyword in question for keyword in ["condition", "diagnosis", "diabetes", "kidney", "renal", "liver", "pregnan", "cancer", "copd", "asthma"]):
        summary = (
            f"Condition-focused answer: {condition_phrase.capitalize()} changes how this medication review should be interpreted."
            if matched_conditions
            else "Condition-focused answer: the current conditions do not match a curated rule, so standard interaction review still applies."
        )
        action_plan = condition_recommendations[:4] or explanation_points[:3]
        return summary, action_plan, [], []

    if any(keyword in question for keyword in ["alternative", "safer", "instead", "replace", "substitute"]):
        summary = "Follow-up answer: consider alternatives only after confirming the interaction severity and the condition-specific risks."
        alternatives = [
            "Consider a non-NSAID pain option if clinically appropriate."
        ] if is_high_risk else ["Review whether a lower-risk alternative exists for this patient context."]
        action_plan = _dedupe_strings([primary_interaction.recommendation, *condition_recommendations])[:4]
        return summary, action_plan, alternatives, []

    summary = (
        "Follow-up answer: this reply is grounded in the current interaction findings, patient conditions, and cited evidence."
    )
    action_plan = explanation_points[:4] or ["Review the current interaction findings with the clinical team."]
    return summary, action_plan, [], []


def generate_advice(request: AdviceRequest) -> AdviceResponse:
    if not request.interactions:
        raise ValueError("No interactions provided")

    max_severity = _max_severity(request.interactions)
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

    if _is_follow_up_question(request.question):
        summary, action_plan, alternatives, red_flags = _build_follow_up_response(
            request,
            condition_recommendations,
            is_high_risk,
        )
    else:
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

        alternatives = ["Consider a non-NSAID pain option if clinically appropriate."] if is_high_risk else []
        red_flags = ["Worsening bruising", "Black stools", "Unexplained bleeding"] if is_high_risk else []

    disclaimer = "Assistive output only. Final decision by licensed clinician."
    if uses_heuristic_evidence:
        disclaimer += " Includes heuristic fallback evidence and requires human validation."
    if condition_recommendations:
        disclaimer += " Includes diagnosis-specific guidance based on the provided conditions."
    if _is_follow_up_question(request.question):
        disclaimer += " Follow-up answers are constrained to the current interaction findings and patient context."

    return AdviceResponse(
        summary=summary,
        action_plan=action_plan,
        alternatives=alternatives,
        red_flags=red_flags,
        citations=[interaction.source for interaction in request.interactions],
        disclaimer=disclaimer,
    )
