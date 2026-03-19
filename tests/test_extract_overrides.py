"""Tests for src/rag/extract_overrides.py — validate_extracted + mocked chain."""

from datetime import date
from unittest.mock import patch, MagicMock

import pytest

from src.models.staff import Staff
from src.rag.extract_overrides import (
    ExtractedOverrides,
    OverrideEntry,
    OffRequestEntry,
    validate_extracted,
    extract_overrides_from_text,
    VALID_OVERRIDE_CODES,
)


# ── Fixtures ──────────────────────────────────────────────────────────

def _staff_and_sections():
    sections = {
        "BAR": [
            Staff(id="bar_1", name="Alice", section="BAR", designation="Bartender"),
            Staff(id="bar_2", name="Bob", section="BAR", designation="Bartender"),
        ],
        "SERVERS": [
            Staff(id="srv_1", name="Dave", section="SERVERS", designation="Server"),
            Staff(id="srv_2", name="Eve", section="SERVERS", designation="Server"),
            Staff(id="srv_3", name="Frank", section="SERVERS", designation="Server"),
        ],
    }
    staff_list = [s for sec in sections.values() for s in sec]
    return staff_list, sections


START = date(2026, 3, 10)
END = date(2026, 3, 16)


# ── validate_extracted: happy paths ──────────────────────────────────

class TestValidateExtractedHappyPaths:
    def test_single_override_resolved(self):
        staff, sections = _staff_and_sections()
        extracted = ExtractedOverrides(
            manual_overrides=[
                OverrideEntry(staff_name="Alice", date_str="2026-03-12", status_code="PH"),
            ],
        )
        warnings, overrides, off_reqs = validate_extracted(extracted, staff, sections, START, END)
        assert warnings == []
        assert overrides == {("bar_1", "2026-03-12"): "PH"}
        assert off_reqs == {}

    def test_off_request_resolved(self):
        staff, sections = _staff_and_sections()
        extracted = ExtractedOverrides(
            off_requests=[
                OffRequestEntry(staff_name="Dave", dates=["2026-03-11", "2026-03-14"]),
            ],
        )
        warnings, overrides, off_reqs = validate_extracted(extracted, staff, sections, START, END)
        assert warnings == []
        assert overrides == {}
        assert off_reqs == {"srv_1": ["2026-03-11", "2026-03-14"]}

    def test_all_keyword_expands_to_every_staff(self):
        staff, sections = _staff_and_sections()
        extracted = ExtractedOverrides(
            manual_overrides=[
                OverrideEntry(staff_name="ALL", date_str="2026-03-15", status_code="PH"),
            ],
        )
        warnings, overrides, _ = validate_extracted(extracted, staff, sections, START, END)
        assert warnings == []
        assert len(overrides) == len(staff)
        assert all(code == "PH" for code in overrides.values())

    def test_section_name_expands_to_section_staff(self):
        staff, sections = _staff_and_sections()
        extracted = ExtractedOverrides(
            manual_overrides=[
                OverrideEntry(staff_name="BAR", date_str="2026-03-13", status_code="V"),
            ],
        )
        warnings, overrides, _ = validate_extracted(extracted, staff, sections, START, END)
        assert warnings == []
        assert set(overrides.keys()) == {("bar_1", "2026-03-13"), ("bar_2", "2026-03-13")}

    def test_all_valid_status_codes_accepted(self):
        staff, sections = _staff_and_sections()
        for code in VALID_OVERRIDE_CODES:
            extracted = ExtractedOverrides(
                manual_overrides=[
                    OverrideEntry(staff_name="Alice", date_str="2026-03-12", status_code=code),
                ],
            )
            warnings, overrides, _ = validate_extracted(extracted, staff, sections, START, END)
            assert warnings == [], f"Code {code} should be valid"
            assert ("bar_1", "2026-03-12") in overrides


# ── validate_extracted: warnings & edge cases ────────────────────────

class TestValidateExtractedWarnings:
    def test_invalid_status_code_skipped(self):
        staff, sections = _staff_and_sections()
        extracted = ExtractedOverrides(
            manual_overrides=[
                OverrideEntry(staff_name="Alice", date_str="2026-03-12", status_code="INVALID"),
            ],
        )
        warnings, overrides, _ = validate_extracted(extracted, staff, sections, START, END)
        assert len(warnings) == 1
        assert "Invalid status code" in warnings[0]
        assert overrides == {}

    def test_date_outside_range_skipped(self):
        staff, sections = _staff_and_sections()
        extracted = ExtractedOverrides(
            manual_overrides=[
                OverrideEntry(staff_name="Alice", date_str="2026-04-01", status_code="PH"),
            ],
        )
        warnings, overrides, _ = validate_extracted(extracted, staff, sections, START, END)
        assert len(warnings) == 1
        assert "outside schedule period" in warnings[0]
        assert overrides == {}

    def test_malformed_date_skipped(self):
        staff, sections = _staff_and_sections()
        extracted = ExtractedOverrides(
            manual_overrides=[
                OverrideEntry(staff_name="Alice", date_str="not-a-date", status_code="PH"),
            ],
        )
        warnings, overrides, _ = validate_extracted(extracted, staff, sections, START, END)
        assert len(warnings) == 1
        assert "Invalid date" in warnings[0]

    def test_unknown_staff_skipped(self):
        staff, sections = _staff_and_sections()
        extracted = ExtractedOverrides(
            manual_overrides=[
                OverrideEntry(staff_name="NoSuchPerson", date_str="2026-03-12", status_code="S"),
            ],
        )
        warnings, overrides, _ = validate_extracted(extracted, staff, sections, START, END)
        assert len(warnings) == 1
        assert "not found in roster" in warnings[0]
        assert overrides == {}

    def test_ambiguous_name_warns_but_applies(self):
        """Two staff with the same name → warning + applied to both."""
        dup_staff = [
            Staff(id="dup_1", name="Sam", section="BAR", designation="Bartender"),
            Staff(id="dup_2", name="Sam", section="BAR", designation="Bartender"),
        ]
        sections = {"BAR": dup_staff}
        extracted = ExtractedOverrides(
            manual_overrides=[
                OverrideEntry(staff_name="Sam", date_str="2026-03-12", status_code="PH"),
            ],
        )
        warnings, overrides, _ = validate_extracted(extracted, dup_staff, sections, START, END)
        assert any("Ambiguous" in w for w in warnings)
        assert len(overrides) == 2

    def test_off_request_unknown_staff(self):
        staff, sections = _staff_and_sections()
        extracted = ExtractedOverrides(
            off_requests=[
                OffRequestEntry(staff_name="Ghost", dates=["2026-03-11"]),
            ],
        )
        warnings, _, off_reqs = validate_extracted(extracted, staff, sections, START, END)
        assert len(warnings) == 1
        assert "not found in roster" in warnings[0]
        assert off_reqs == {}

    def test_off_request_date_outside_range(self):
        staff, sections = _staff_and_sections()
        extracted = ExtractedOverrides(
            off_requests=[
                OffRequestEntry(staff_name="Eve", dates=["2026-03-11", "2026-05-01"]),
            ],
        )
        warnings, _, off_reqs = validate_extracted(extracted, staff, sections, START, END)
        assert any("outside period" in w for w in warnings)
        assert off_reqs == {"srv_2": ["2026-03-11"]}

    def test_empty_extraction_is_fine(self):
        staff, sections = _staff_and_sections()
        extracted = ExtractedOverrides()
        warnings, overrides, off_reqs = validate_extracted(extracted, staff, sections, START, END)
        assert warnings == []
        assert overrides == {}
        assert off_reqs == {}

    def test_mixed_valid_and_invalid(self):
        staff, sections = _staff_and_sections()
        extracted = ExtractedOverrides(
            manual_overrides=[
                OverrideEntry(staff_name="Alice", date_str="2026-03-12", status_code="PH"),
                OverrideEntry(staff_name="Ghost", date_str="2026-03-12", status_code="S"),
                OverrideEntry(staff_name="Bob", date_str="bad-date", status_code="V"),
            ],
            off_requests=[
                OffRequestEntry(staff_name="Dave", dates=["2026-03-14"]),
                OffRequestEntry(staff_name="Nobody", dates=["2026-03-11"]),
            ],
        )
        warnings, overrides, off_reqs = validate_extracted(extracted, staff, sections, START, END)
        assert len(warnings) == 3  # Ghost, bad-date, Nobody
        assert ("bar_1", "2026-03-12") in overrides
        assert "srv_1" in off_reqs


# ── extract_overrides_from_text (mocked LLM) ────────────────────────

class TestExtractOverridesFromTextMocked:
    @patch("src.rag.extract_overrides._EXTRACT_PROMPT")
    @patch("src.rag.extract_overrides._get_llm")
    def test_chain_receives_correct_payload(self, mock_get_llm, mock_prompt):
        staff, sections = _staff_and_sections()

        fake_result = ExtractedOverrides(
            manual_overrides=[
                OverrideEntry(staff_name="Alice", date_str="2026-03-12", status_code="PH"),
            ],
        )

        mock_chain = MagicMock()
        mock_chain.invoke.return_value = fake_result
        mock_prompt.__or__ = MagicMock(return_value=mock_chain)

        mock_llm = MagicMock()
        mock_llm.with_structured_output.return_value = MagicMock()
        mock_get_llm.return_value = mock_llm

        result = extract_overrides_from_text(
            text="PH on 12th for Alice",
            staff_list=staff,
            sections=sections,
            start_date=START,
            end_date=END,
        )

        mock_llm.with_structured_output.assert_called_once_with(ExtractedOverrides)
        assert isinstance(result, ExtractedOverrides)
        assert result.manual_overrides[0].staff_name == "Alice"
