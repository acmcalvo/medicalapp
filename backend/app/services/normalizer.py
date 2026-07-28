from app.schemas.clinical import MedicationInput


def normalize_medications(medications: list[MedicationInput]) -> list[dict[str, str]]:
    return [{"name_entered": med.name_entered, "normalized": med.name_entered.lower()} for med in medications]
