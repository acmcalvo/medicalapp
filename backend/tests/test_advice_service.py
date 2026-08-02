from app.schemas.clinical import AdviceRequest, InteractionItem, PatientContext
from app.services.advice_service import generate_advice


def test_generate_advice_includes_condition_specific_recommendations() -> None:
    request = AdviceRequest(
        role="pharmacist",
        patient=PatientContext(
            conditions=["Diabetes", "Lung cancer", "Hypertension", "Kidney disease"],
        ),
        interactions=[
            InteractionItem(
                drug_a="Prednisone",
                drug_b="Diabetes",
                severity="major",
                source_type="heuristic",
                mechanism="Systemic corticosteroids can raise blood glucose.",
                clinical_effect="Risk of hyperglycemia.",
                recommendation="Use the lowest effective steroid dose and coordinate glucose management.",
                monitoring=["Monitor blood glucose frequently"],
                source="Fallback condition-medication rule | DailyMed label: Prednisone",
            )
        ],
        question="Summarize the medication review for clinician sign-off.",
    )

    response = generate_advice(request)

    assert any("blood sugar closely" in item for item in response.action_plan)
    assert any("pulmonary vulnerability" in item for item in response.action_plan)
    assert any("monitor blood pressure" in item.lower() for item in response.action_plan)
    assert any("renal dosing" in item.lower() for item in response.action_plan)
    assert "diagnosis-specific guidance" in response.disclaimer
    assert "Diagnosis-aware review" in response.summary or "Provisional diagnosis-aware finding" in response.summary


def test_generate_advice_answers_condition_follow_up_question() -> None:
    request = AdviceRequest(
        role="pharmacist",
        patient=PatientContext(
            conditions=["Diabetes"],
        ),
        interactions=[
            InteractionItem(
                drug_a="Condition: Diabetes",
                drug_b="Prednisone",
                severity="major",
                source_type="heuristic",
                mechanism="Systemic corticosteroids can raise blood glucose and worsen glycemic control.",
                clinical_effect="Risk of hyperglycemia and increased need for diabetes therapy adjustments.",
                recommendation="Use the lowest effective steroid dose and coordinate glucose management during treatment.",
                monitoring=["Monitor blood glucose frequently", "Review diabetes medication plan"],
                source="Fallback condition-medication rule | DailyMed label: Prednisone",
            )
        ],
        question="How does diabetes change this interaction?",
    )

    response = generate_advice(request)

    assert response.summary.startswith("Condition-focused answer:")
    assert any("blood sugar closely" in item.lower() or "glucose" in item.lower() for item in response.action_plan)
    assert "Follow-up answers are constrained" in response.disclaimer


def test_generate_advice_answers_monitoring_follow_up_question() -> None:
    request = AdviceRequest(
        role="doctor",
        patient=PatientContext(
            conditions=["Diabetes"],
        ),
        interactions=[
            InteractionItem(
                drug_a="Condition: Diabetes",
                drug_b="Prednisone",
                severity="major",
                source_type="heuristic",
                mechanism="Systemic corticosteroids can raise blood glucose and worsen glycemic control.",
                clinical_effect="Risk of hyperglycemia and increased need for diabetes therapy adjustments.",
                recommendation="Use the lowest effective steroid dose and coordinate glucose management during treatment.",
                monitoring=["Monitor blood glucose frequently", "Review diabetes medication plan"],
                source="Fallback condition-medication rule | DailyMed label: Prednisone",
            )
        ],
        question="What should I monitor here?",
    )

    response = generate_advice(request)

    assert response.summary.startswith("Follow-up answer:")
    assert any("blood glucose" in item.lower() for item in response.action_plan)
    assert response.red_flags