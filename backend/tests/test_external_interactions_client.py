from app.services.external_interactions_client import _extract_interaction_list, _map_external_item


def test_extract_interaction_list_supports_pairwise_shape() -> None:
    payload = {
        "pairwise": [
            {
                "drug1": "warfarin",
                "drug2": "digoxin",
                "severity": "moderate",
            }
        ]
    }

    items = _extract_interaction_list(payload)

    assert len(items) == 1
    assert items[0]["drug1"] == "warfarin"


def test_map_external_item_handles_stringified_interaction_block() -> None:
    raw_item = {
        "drug1": "warfarin",
        "drug2": "digoxin",
        "interaction": "{'description': 'This interaction is usually moderate in severity.', 'severity': 'moderate'}",
        "source": "PAIRWISE's drug interactions",
    }

    mapped = _map_external_item(raw_item)

    assert mapped["drug_a"] == "warfarin"
    assert mapped["drug_b"] == "digoxin"
    assert mapped["severity"] == "moderate"
    assert "moderate" in mapped["mechanism"].lower()