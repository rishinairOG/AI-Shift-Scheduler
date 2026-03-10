from src.parser.roster_parser import parse_roster

ROSTER_PATH = "C:/Users/rishi/OneDrive/Desktop/WR KSA/WR_FOH/FOH WR KSA/Duty roster - New Format.xlsx"


def test_parser_returns_staff():
    staff_list, sections = parse_roster(ROSTER_PATH)
    assert len(staff_list) > 0, "Parser returned no staff"


def test_parser_sections_present():
    staff_list, sections = parse_roster(ROSTER_PATH)
    expected = {"MANAGERS", "ASST. MANAGERS", "SUPERVISORS", "SERVERS", "GRE", "BAR"}
    found = set(sections.keys())
    assert expected.issubset(found), f"Missing sections: {expected - found}"


def test_staff_have_names():
    staff_list, _ = parse_roster(ROSTER_PATH)
    for s in staff_list:
        assert s.name.strip(), f"Staff has empty name: {s}"


def test_staff_have_sections():
    staff_list, _ = parse_roster(ROSTER_PATH)
    for s in staff_list:
        assert s.section, f"Staff {s.name} has no section"
