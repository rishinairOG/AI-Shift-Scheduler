"""
Structured extraction: free text → manual_overrides + off_requests.
Uses LangChain structured output to parse manager instructions into
typed override and OFF-request dicts matching ScheduleConfig format.
"""

import os
from datetime import date
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate

from src.models.staff import Staff


class OverrideEntry(BaseModel):
    staff_name: str = Field(description="Staff name exactly as it appears in the roster, or 'ALL' for everyone")
    date_str: str = Field(description="Date in YYYY-MM-DD format")
    status_code: str = Field(description="One of: PH, HP, S, HD, HO, TR, V")


class OffRequestEntry(BaseModel):
    staff_name: str = Field(description="Staff name exactly as it appears in the roster")
    dates: list[str] = Field(description="List of dates in YYYY-MM-DD format")


class ExtractedOverrides(BaseModel):
    manual_overrides: list[OverrideEntry] = Field(
        default_factory=list,
        description="Manual status overrides (PH, S, V, TR, HD, HO, HP)"
    )
    off_requests: list[OffRequestEntry] = Field(
        default_factory=list,
        description="Staff OFF day requests"
    )


_EXTRACT_PROMPT = ChatPromptTemplate.from_messages([
    ("system",
     "You are a scheduling assistant. Extract manual overrides and OFF requests "
     "from the manager's free-text instructions.\n\n"
     "STAFF ROSTER (use these exact names):\n{roster}\n\n"
     "SECTIONS: {sections}\n\n"
     "SCHEDULE PERIOD: {start_date} to {end_date}\n\n"
     "RULES:\n"
     "- Status codes: PH (Public Holiday), HP (Half Public Holiday), S (Sick Leave), "
     "HD (Half Day), HO (Half Off Day), TR (Transferred), V (Vacation)\n"
     "- 'OFF' requests go into off_requests (not manual_overrides)\n"
     "- If the text says 'everyone' or a section name, expand to individual staff entries using staff_name='ALL'\n"
     "- All dates must be YYYY-MM-DD format and fall within the schedule period\n"
     "- Resolve relative dates (e.g. '21st') using the schedule period's month/year\n"
     ),
    ("human", "{text}"),
])


def _get_llm() -> ChatOpenAI:
    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    model = os.environ.get("OPENROUTER_MODEL", "openai/gpt-4o-mini")
    return ChatOpenAI(
        model=model,
        openai_api_key=api_key,
        openai_api_base="https://openrouter.ai/api/v1",
        temperature=0,
        max_tokens=1024,
    )


def extract_overrides_from_text(
    text: str,
    staff_list: list[Staff],
    sections: dict,
    start_date: date,
    end_date: date,
) -> ExtractedOverrides:
    """Parse free-text instructions into structured overrides and OFF requests."""
    roster_str = "\n".join(
        f"- {s.name} (section: {s.section}, designation: {s.designation})"
        for s in staff_list
    )
    section_names = ", ".join(sections.keys())

    llm = _get_llm()
    structured_llm = llm.with_structured_output(ExtractedOverrides)

    chain = _EXTRACT_PROMPT | structured_llm
    result = chain.invoke({
        "roster": roster_str,
        "sections": section_names,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "text": text,
    })
    return result


VALID_OVERRIDE_CODES = {"PH", "HP", "S", "HD", "HO", "TR", "V"}


def validate_extracted(
    extracted: ExtractedOverrides,
    staff_list: list[Staff],
    sections: dict,
    start_date: date,
    end_date: date,
) -> tuple[list[str], dict, dict]:
    """
    Validate and resolve extracted overrides against the roster.
    Returns (warnings, resolved_overrides, resolved_off_requests).
    - resolved_overrides: {(staff_id, date_str): code}
    - resolved_off_requests: {staff_id: [date_str, ...]}
    """
    warnings = []
    resolved_overrides: dict[tuple[str, str], str] = {}
    resolved_off_requests: dict[str, list[str]] = {}

    staff_by_name = {}
    for s in staff_list:
        staff_by_name.setdefault(s.name.lower(), []).append(s)

    all_section_staff = {
        sec.upper(): [s for s in staffers]
        for sec, staffers in sections.items()
    }

    for entry in extracted.manual_overrides:
        code = entry.status_code.upper()
        if code not in VALID_OVERRIDE_CODES:
            warnings.append(f"Invalid status code '{entry.status_code}' — skipped.")
            continue

        try:
            d = date.fromisoformat(entry.date_str)
            if d < start_date or d > end_date:
                warnings.append(f"Date {entry.date_str} is outside schedule period — skipped.")
                continue
        except ValueError:
            warnings.append(f"Invalid date '{entry.date_str}' — skipped.")
            continue

        name_key = entry.staff_name.strip().lower()

        if name_key == "all":
            for s in staff_list:
                resolved_overrides[(s.id, entry.date_str)] = code
        elif name_key.upper() in all_section_staff:
            for s in all_section_staff[name_key.upper()]:
                resolved_overrides[(s.id, entry.date_str)] = code
        elif name_key in staff_by_name:
            matches = staff_by_name[name_key]
            if len(matches) > 1:
                warnings.append(
                    f"Ambiguous name '{entry.staff_name}' matches {len(matches)} staff — applied to all matches."
                )
            for s in matches:
                resolved_overrides[(s.id, entry.date_str)] = code
        else:
            warnings.append(f"Staff '{entry.staff_name}' not found in roster — skipped.")

    for entry in extracted.off_requests:
        name_key = entry.staff_name.strip().lower()
        if name_key not in staff_by_name:
            warnings.append(f"Staff '{entry.staff_name}' not found in roster — OFF request skipped.")
            continue

        matches = staff_by_name[name_key]
        if len(matches) > 1:
            warnings.append(
                f"Ambiguous name '{entry.staff_name}' matches {len(matches)} staff — OFF request applied to all."
            )

        valid_dates = []
        for dstr in entry.dates:
            try:
                d = date.fromisoformat(dstr)
                if d < start_date or d > end_date:
                    warnings.append(f"OFF date {dstr} for {entry.staff_name} is outside period — skipped.")
                    continue
                valid_dates.append(dstr)
            except ValueError:
                warnings.append(f"Invalid OFF date '{dstr}' for {entry.staff_name} — skipped.")

        for s in matches:
            resolved_off_requests.setdefault(s.id, []).extend(valid_dates)

    return warnings, resolved_overrides, resolved_off_requests
