"""Proves every legal parameter the engine evaluates against is genuinely read
from rule_pack_v1.json at runtime — not hardcoded in Python — and that a broken
rule pack fails loudly instead of silently falling back to an invented value.

These tests build TEMPORARY, mutated copies of the real rule pack under `tmp_path`
rather than editing docs/legal/rule_pack_v1.json itself — the verified legal
source is never touched by a test.
"""

import inspect
import json
from pathlib import Path

import pytest

from app.config import get_settings
from app.pipeline import rule_engine
from app.pipeline.extraction import ExtractedFieldData
from app.pipeline.rule_engine import STATUS_FAIL, STATUS_PASS, RulePackValidationError, evaluate_field

REAL_RULE_PACK_PATH = get_settings().rule_pack_path
THRESHOLD = 60.0


def _load_real_rule_pack_data() -> dict:
    return json.loads(REAL_RULE_PACK_PATH.read_bytes())


def _write_rule_pack(tmp_path: Path, data: dict, name: str = "rule_pack_test.json") -> str:
    path = tmp_path / name
    path.write_text(json.dumps(data))
    return str(path)


def _field_by_id(data: dict, field_id: str) -> dict:
    return next(f for f in data["fields"] if f["field_id"] == field_id)


# --- 1 & 2: Table II tolerance is genuinely data-driven ----------------------------


def test_table_ii_tolerance_is_loaded_from_json(tmp_path):
    data = _load_real_rule_pack_data()
    rule_pack = rule_engine.load_rule_pack(_write_rule_pack(tmp_path, data))
    field_spec = rule_pack.fields_by_id()["net_quantity"]
    expected_pct = field_spec["tolerance_table_length_area_number"]["entries"]["number"]["percentage"]

    extracted = ExtractedFieldData(field_id="net_quantity", found=True, raw_value="10 nos", confidence=95.0)
    result = evaluate_field(field_spec, extracted, THRESHOLD, rule_pack.version)

    assert result.status == STATUS_PASS
    assert result.evidence["applicable_tolerance"]["pct"] == expected_pct
    assert result.evidence["applicable_tolerance"]["max_error_units"] == round(10 * expected_pct / 100, 2)


def test_changing_json_percentage_changes_evaluation_behavior(tmp_path):
    data = _load_real_rule_pack_data()
    _field_by_id(data, "net_quantity")["tolerance_table_length_area_number"]["entries"]["number"]["percentage"] = 9.0
    rule_pack = rule_engine.load_rule_pack(_write_rule_pack(tmp_path, data))
    field_spec = rule_pack.fields_by_id()["net_quantity"]

    extracted = ExtractedFieldData(field_id="net_quantity", found=True, raw_value="10 nos", confidence=95.0)
    result = evaluate_field(field_spec, extracted, THRESHOLD, rule_pack.version)

    assert result.evidence["applicable_tolerance"]["pct"] == 9.0
    assert result.evidence["applicable_tolerance"]["max_error_units"] == 0.9  # 10 * 9% — not the real pack's 0.2 (2%)


# --- 3: no Python fallback for the legal percentage ---------------------------------


def test_lookup_count_tolerance_has_no_default_table_parameter():
    sig = inspect.signature(rule_engine.lookup_count_tolerance)
    assert sig.parameters["table"].default is inspect.Parameter.empty, (
        "lookup_count_tolerance must require the table explicitly — a default would "
        "make it possible to silently evaluate against an invented percentage."
    )


def test_lookup_count_tolerance_raises_without_a_number_entry():
    with pytest.raises(KeyError):
        rule_engine.lookup_count_tolerance(10, {"entries": {}})


# --- 4 & 5: clause references in verdicts come from the rule pack, not literals ----


def test_clause_in_verdict_reason_comes_from_rule_pack(tmp_path):
    data = _load_real_rule_pack_data()
    rule_pack = rule_engine.load_rule_pack(_write_rule_pack(tmp_path, data))
    field_spec = rule_pack.fields_by_id()["retail_sale_price"]

    extracted = ExtractedFieldData(field_id="retail_sale_price", found=True, raw_value="Rs. 100.00", confidence=95.0)
    result = evaluate_field(field_spec, extracted, THRESHOLD, rule_pack.version)

    assert result.status == STATUS_FAIL
    assert field_spec["clause"] in result.reason
    assert result.legal_reference == field_spec["legal_reference"]


def test_changing_clause_in_test_rule_pack_changes_generated_reason(tmp_path):
    data = _load_real_rule_pack_data()
    _field_by_id(data, "retail_sale_price")["clause"] = "Rule 6(1)(e)-TEST-MARKER"
    rule_pack = rule_engine.load_rule_pack(_write_rule_pack(tmp_path, data))
    field_spec = rule_pack.fields_by_id()["retail_sale_price"]

    extracted = ExtractedFieldData(field_id="retail_sale_price", found=True, raw_value="Rs. 100.00", confidence=95.0)
    result = evaluate_field(field_spec, extracted, THRESHOLD, rule_pack.version)

    # This marker exists ONLY in the temporary test rule pack — if rule_engine.py had
    # "Rule 6(1)(e)" hardcoded anywhere in this reason string, it could not appear.
    assert "Rule 6(1)(e)-TEST-MARKER" in result.reason


def test_net_quantity_invalid_unit_reason_uses_rule_pack_clause(tmp_path):
    data = _load_real_rule_pack_data()
    _field_by_id(data, "net_quantity")["clause"] = "Rule 6(1)(c)-TEST-MARKER"
    rule_pack = rule_engine.load_rule_pack(_write_rule_pack(tmp_path, data))
    field_spec = rule_pack.fields_by_id()["net_quantity"]

    extracted = ExtractedFieldData(field_id="net_quantity", found=True, raw_value="900", confidence=95.0)
    result = evaluate_field(field_spec, extracted, THRESHOLD, rule_pack.version)

    assert result.status == STATUS_FAIL
    assert "Rule 6(1)(c)-TEST-MARKER" in result.reason


# --- 6 & 7: a broken rule pack fails loudly at load time, never silently ------------


def test_missing_table_ii_percentage_fails_loudly(tmp_path):
    data = _load_real_rule_pack_data()
    del _field_by_id(data, "net_quantity")["tolerance_table_length_area_number"]["entries"]["number"]["percentage"]
    path = _write_rule_pack(tmp_path, data)

    with pytest.raises(RulePackValidationError, match="percentage"):
        rule_engine.load_rule_pack(path)


def test_malformed_table_ii_percentage_fails_loudly(tmp_path):
    data = _load_real_rule_pack_data()
    _field_by_id(data, "net_quantity")["tolerance_table_length_area_number"]["entries"]["number"]["percentage"] = (
        "two percent"
    )
    path = _write_rule_pack(tmp_path, data)

    with pytest.raises(RulePackValidationError, match="percentage"):
        rule_engine.load_rule_pack(path)


def test_negative_table_ii_percentage_fails_loudly(tmp_path):
    data = _load_real_rule_pack_data()
    _field_by_id(data, "net_quantity")["tolerance_table_length_area_number"]["entries"]["number"]["percentage"] = -2.0
    path = _write_rule_pack(tmp_path, data)

    with pytest.raises(RulePackValidationError, match="percentage"):
        rule_engine.load_rule_pack(path)


def test_missing_clause_fails_loudly(tmp_path):
    data = _load_real_rule_pack_data()
    del _field_by_id(data, "retail_sale_price")["clause"]
    path = _write_rule_pack(tmp_path, data)

    with pytest.raises(RulePackValidationError, match="clause"):
        rule_engine.load_rule_pack(path)


def test_empty_clause_fails_loudly(tmp_path):
    data = _load_real_rule_pack_data()
    _field_by_id(data, "retail_sale_price")["clause"] = "   "
    path = _write_rule_pack(tmp_path, data)

    with pytest.raises(RulePackValidationError, match="clause"):
        rule_engine.load_rule_pack(path)


def test_missing_weight_volume_table_fails_loudly(tmp_path):
    data = _load_real_rule_pack_data()
    del _field_by_id(data, "net_quantity")["tolerance_table_weight_volume"]
    path = _write_rule_pack(tmp_path, data)

    with pytest.raises(RulePackValidationError, match="tolerance_table_weight_volume"):
        rule_engine.load_rule_pack(path)


def test_valid_real_rule_pack_still_loads_cleanly():
    # The real, unmodified legal rule pack must pass its own validation.
    rule_pack = rule_engine.load_rule_pack(str(REAL_RULE_PACK_PATH))
    assert rule_pack.version == "1"
    assert len(rule_pack.fields) == 7
