import pytest

from app.config import get_settings
from app.pipeline import rule_engine
from app.pipeline.extraction import ExtractedFieldData
from app.pipeline.rule_engine import (
    STATUS_FAIL,
    STATUS_NOT_APPLICABLE,
    STATUS_PASS,
    STATUS_REVIEW,
    aggregate_verdict_from_statuses,
    evaluate_field,
    lookup_length_area_tolerance,
    lookup_weight_volume_tolerance,
    parse_quantity,
)

RULE_PACK = rule_engine.load_rule_pack(str(get_settings().rule_pack_path))
FIELDS_BY_ID = RULE_PACK.fields_by_id()
THRESHOLD = 60.0


def test_rule_pack_loads_all_seven_mvp_fields():
    assert RULE_PACK.version == "1"
    assert len(RULE_PACK.fields) == 7
    assert set(FIELDS_BY_ID) == {
        "manufacturer_packer_importer",
        "country_of_origin",
        "common_generic_name",
        "net_quantity",
        "date_of_manufacture",
        "retail_sale_price",
        "consumer_care_details",
    }


def test_rule_pack_hash_is_reproducible():
    reloaded = rule_engine.load_rule_pack(str(get_settings().rule_pack_path))
    assert reloaded.sha256_hash == RULE_PACK.sha256_hash
    assert len(RULE_PACK.sha256_hash) == 64  # sha256 hex digest


# --- net quantity: First Schedule Table I band lookup + rounding -------------------


@pytest.mark.parametrize(
    "declared_g_ml, expected_basis, expected_error",
    [
        (10, "percentage", 0.9),  # up to 50: 9% of 10 = 0.9
        (50, "percentage", 4.5),  # boundary belongs to "up to 50" band: 9% of 50 = 4.5
        (75, "absolute", 4.5),  # 50 to 100: absolute 4.5
        (150, "percentage", 6.8),  # 100 to 200: 4.5% of 150 = 6.75 -> rounds to 6.8
        (250, "absolute", 9),  # 200 to 300: absolute 9
        (400, "percentage", 12.0),  # 300 to 500: 3% of 400 = 12
        (750, "absolute", 15),  # 500 to 1000: absolute 15
        (5000, "percentage", 75.0),  # 1000 to 10000: 1.5% of 5000 = 75, rounds to whole above 1000
        (12000, "absolute", 150),  # 10000 to 15000: absolute 150
        (20000, "percentage", 200),  # more than 15000: 1% of 20000 = 200
    ],
)
def test_weight_volume_tolerance_bands(declared_g_ml, expected_basis, expected_error):
    table = FIELDS_BY_ID["net_quantity"]["tolerance_table_weight_volume"]
    tol = lookup_weight_volume_tolerance(declared_g_ml, table)
    assert tol is not None
    assert tol["basis"] == expected_basis
    assert tol["max_error_g_or_ml"] == expected_error


def test_parse_quantity_recognises_units():
    assert parse_quantity("900 g").canonical_value == 900
    assert parse_quantity("1.5 kg").canonical_value == 1500
    assert parse_quantity("500ml").canonical_value == 500
    assert parse_quantity("2 L").canonical_value == 2000
    assert parse_quantity("10 nos").kind == "count"


def test_parse_quantity_rejects_missing_unit():
    assert parse_quantity("900") is None
    assert parse_quantity("net weight unclear") is None


# --- length/area units: a real false-NON_COMPLIANT bug found via a hostile-judge
# audit (a rope/cable/fabric declared by length was failed as "no recognised
# standard unit", which is legally wrong — metre is a recognised standard unit) --


def test_parse_quantity_recognises_length_units():
    assert parse_quantity("10 metre").kind == "length"
    assert parse_quantity("10 metre").canonical_value == 10
    assert parse_quantity("15 m").canonical_value == 15
    assert parse_quantity("100 cm").canonical_value == 1  # 100cm -> 1m
    assert parse_quantity("2 km").canonical_value == 2000


def test_parse_quantity_recognises_area_units():
    for text in ("10 sq m", "10 sqm", "10 sq. m", "10 sq metre", "10 square metre"):
        parsed = parse_quantity(text)
        assert parsed is not None, f"failed to parse {text!r}"
        assert parsed.kind == "area"
        assert parsed.canonical_value == 10


def test_length_area_tolerance_uses_threshold_from_rule_pack():
    table = FIELDS_BY_ID["net_quantity"]["tolerance_table_length_area_number"]
    # At/below the 10-metre threshold: the lower rate (2%) applies.
    at_threshold = lookup_length_area_tolerance("length", 10, table)
    assert at_threshold["pct"] == 2.0
    assert at_threshold["max_error"] == 0.2
    # Above the threshold: the higher rate (1%) applies.
    above_threshold = lookup_length_area_tolerance("length", 15, table)
    assert above_threshold["pct"] == 1.0
    assert above_threshold["max_error"] == 0.15
    # Area uses its own 4%/1% rates, not length's 2%/1%.
    area_at_threshold = lookup_length_area_tolerance("area", 10, table)
    assert area_at_threshold["pct"] == 4.0


def test_net_quantity_declared_by_length_passes_not_fails():
    """Regression test for the false-NON_COMPLIANT bug: a product legitimately
    sold by length must PASS, not FAIL with a claim that metre isn't a
    recognised unit."""
    extracted = ExtractedFieldData(field_id="net_quantity", found=True, raw_value="10 metre", confidence=95.0)
    result = evaluate_field(FIELDS_BY_ID["net_quantity"], extracted, THRESHOLD, RULE_PACK.version)
    assert result.status == STATUS_PASS
    assert result.evidence["applicable_tolerance"]["pct"] == 2.0


def test_net_quantity_declared_by_area_passes_not_fails():
    extracted = ExtractedFieldData(field_id="net_quantity", found=True, raw_value="5 sq m", confidence=95.0)
    result = evaluate_field(FIELDS_BY_ID["net_quantity"], extracted, THRESHOLD, RULE_PACK.version)
    assert result.status == STATUS_PASS
    assert result.evidence["applicable_tolerance"]["pct"] == 4.0


# --- field evaluation: presence, confidence gating, conditional fields -------------


def test_missing_field_is_review_not_fail():
    extracted = ExtractedFieldData(field_id="manufacturer_packer_importer", found=False)
    result = evaluate_field(FIELDS_BY_ID["manufacturer_packer_importer"], extracted, THRESHOLD, RULE_PACK.version)
    assert result.status == STATUS_REVIEW
    assert "not detected" in result.reason.lower()


def test_low_confidence_forces_review_even_when_value_looks_valid():
    extracted = ExtractedFieldData(
        field_id="manufacturer_packer_importer", found=True, raw_value="ULTRON Foods Pvt Ltd", confidence=42.0
    )
    result = evaluate_field(FIELDS_BY_ID["manufacturer_packer_importer"], extracted, THRESHOLD, RULE_PACK.version)
    assert result.status == STATUS_REVIEW
    assert "confidence" in result.reason.lower()


def test_high_confidence_presence_field_passes():
    extracted = ExtractedFieldData(
        field_id="manufacturer_packer_importer", found=True, raw_value="ULTRON Foods Pvt Ltd", confidence=95.0
    )
    result = evaluate_field(FIELDS_BY_ID["manufacturer_packer_importer"], extracted, THRESHOLD, RULE_PACK.version)
    assert result.status == STATUS_PASS


def test_country_of_origin_not_applicable_when_domestic():
    extracted = ExtractedFieldData(field_id="country_of_origin", found=False, applicable=False)
    result = evaluate_field(FIELDS_BY_ID["country_of_origin"], extracted, THRESHOLD, RULE_PACK.version)
    assert result.status == STATUS_NOT_APPLICABLE


def test_country_of_origin_required_when_imported():
    extracted = ExtractedFieldData(field_id="country_of_origin", found=True, applicable=True, raw_value="China", confidence=90.0)
    result = evaluate_field(FIELDS_BY_ID["country_of_origin"], extracted, THRESHOLD, RULE_PACK.version)
    assert result.status == STATUS_PASS


def test_net_quantity_invalid_unit_fails():
    extracted = ExtractedFieldData(field_id="net_quantity", found=True, raw_value="900", confidence=95.0)
    result = evaluate_field(FIELDS_BY_ID["net_quantity"], extracted, THRESHOLD, RULE_PACK.version)
    assert result.status == STATUS_FAIL
    assert "standard unit" in result.reason.lower()


def test_net_quantity_valid_unit_passes_with_tolerance_evidence():
    extracted = ExtractedFieldData(field_id="net_quantity", found=True, raw_value="900 g", confidence=95.0)
    result = evaluate_field(FIELDS_BY_ID["net_quantity"], extracted, THRESHOLD, RULE_PACK.version)
    assert result.status == STATUS_PASS
    assert result.evidence["applicable_tolerance"] is not None


def test_mrp_without_inclusive_of_taxes_fails():
    extracted = ExtractedFieldData(field_id="retail_sale_price", found=True, raw_value="Rs. 150.00", confidence=95.0)
    result = evaluate_field(FIELDS_BY_ID["retail_sale_price"], extracted, THRESHOLD, RULE_PACK.version)
    assert result.status == STATUS_FAIL
    assert "6(1)(e)" in result.legal_reference


def test_mrp_with_inclusive_of_taxes_passes():
    extracted = ExtractedFieldData(field_id="retail_sale_price", found=True, raw_value="Rs. 150.00 incl. of all taxes", confidence=95.0)
    result = evaluate_field(FIELDS_BY_ID["retail_sale_price"], extracted, THRESHOLD, RULE_PACK.version)
    assert result.status == STATUS_PASS


# --- verdict aggregation: FAIL > REVIEW > COMPLIANT priority -----------------------


def test_aggregate_all_pass_is_compliant():
    assert aggregate_verdict_from_statuses([STATUS_PASS, STATUS_PASS, STATUS_NOT_APPLICABLE]) == "COMPLIANT"


def test_aggregate_any_fail_is_non_compliant_even_with_reviews():
    assert aggregate_verdict_from_statuses([STATUS_PASS, STATUS_REVIEW, STATUS_FAIL]) == "NON_COMPLIANT"


def test_aggregate_review_without_fail_is_review():
    assert aggregate_verdict_from_statuses([STATUS_PASS, STATUS_REVIEW, STATUS_NOT_APPLICABLE]) == "REVIEW"


def test_aggregate_all_not_applicable_falls_back_to_review():
    assert aggregate_verdict_from_statuses([STATUS_NOT_APPLICABLE]) == "REVIEW"
