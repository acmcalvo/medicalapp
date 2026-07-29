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