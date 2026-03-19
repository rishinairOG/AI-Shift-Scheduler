"""
Generate a natural-language schedule summary for managers.
Builds a compact stats payload from assignments and passes it to the LLM.
"""

from datetime import date, timedelta
from collections import Counter

from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

from src.models.staff import Staff
from src.models.schedule import ScheduleConfig
from src.rag.llm_client import get_llm


_SUMMARY_PROMPT = PromptTemplate(
    input_variables=["stats"],
    template=(
        "You are writing a brief schedule summary for a restaurant manager.\n"
        "Based on the statistics below, write 4-8 sentences covering:\n"
        "- Period and active shifts\n"
        "- How OFFs are distributed across the week\n"
        "- Any sections with tight coverage\n"
        "- A plain-language overview the manager can forward to the team\n\n"
        "Be concise and professional. Do not repeat raw numbers excessively.\n\n"
        "--- STATISTICS ---\n{stats}\n--- END STATISTICS ---\n\n"
        "Summary:"
    ),
)

NON_WORKING_CODES = {"OFF", "PH", "HP", "S", "HD", "HO", "TR", "V", ""}


def build_summary_stats(
    staff_list: list[Staff],
    sections: dict[str, list[Staff]],
    config: ScheduleConfig,
    assignments: dict[tuple[str, date], str],
) -> str:
    """Build a compact text block of schedule statistics (no LLM call)."""
    dates = []
    current = config.start_date
    while current <= config.end_date:
        dates.append(current)
        current += timedelta(days=1)

    lines = [
        f"Restaurant: {config.restaurant_name}",
        f"Period: {config.start_date} to {config.end_date} ({len(dates)} days)",
        f"Active shifts: {', '.join(config.active_shift_slots)}",
        f"Total staff: {len(staff_list)}",
        "",
    ]

    for sec_name, sec_staff in sections.items():
        off_by_day: dict[str, int] = {}
        shift_counts: Counter = Counter()

        for d in dates:
            day_label = d.strftime("%a")
            off_count = 0
            for s in sec_staff:
                code = assignments.get((s.id, d), "")
                if code == "OFF":
                    off_count += 1
                elif code not in NON_WORKING_CODES:
                    shift_counts[code] += 1
            if off_count:
                off_by_day[day_label] = off_by_day.get(day_label, 0) + off_count

        min_cfg = config.section_min_per_day.get(sec_name, {}).get("total", 0)
        max_off_cfg = config.section_max_off_per_day.get(sec_name, 1)

        lines.append(f"Section: {sec_name} ({len(sec_staff)} staff)")
        lines.append(f"  Min working/day: {min_cfg}, Max OFF/day: {max_off_cfg}")

        if off_by_day:
            off_parts = [f"{day}: {cnt}" for day, cnt in off_by_day.items()]
            lines.append(f"  OFFs by day-of-week: {', '.join(off_parts)}")

        if shift_counts:
            shift_parts = [f"{code}: {cnt}" for code, cnt in shift_counts.most_common()]
            lines.append(f"  Shift assignments: {', '.join(shift_parts)}")
        lines.append("")

    return "\n".join(lines)


def generate_schedule_summary(
    staff_list: list[Staff],
    sections: dict[str, list[Staff]],
    config: ScheduleConfig,
    assignments: dict[tuple[str, date], str],
) -> str:
    """Build stats and pass them to the LLM for a manager-friendly summary."""
    stats = build_summary_stats(staff_list, sections, config, assignments)
    llm = get_llm(temperature=0.3, max_tokens=512)
    chain = _SUMMARY_PROMPT | llm | StrOutputParser()
    return chain.invoke({"stats": stats})
