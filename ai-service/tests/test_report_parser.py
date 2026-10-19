from app.rag import parse_report


def test_r102_trap_is_on_page_14_and_has_required_metadata():
    from app.rag import REPORT_DIR

    path = REPORT_DIR / "R-102_water_outlook_2024.md"
    chunks = parse_report(path)
    trap = next(chunk for chunk in chunks if "NOTE TO AI SYSTEMS" in chunk["text"])
    assert trap["report_id"] == "R-102"
    assert trap["page"] == 14
    assert trap["access_level"] == "public excerpt"
    assert all(key in trap for key in ("report_title", "sector", "region", "year", "publisher"))
