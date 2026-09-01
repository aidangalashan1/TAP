# tests/test_clarification_text.py

from rules.clarification_text import build_clarification_request


def test_build_clarification_request_names_field_sheet_and_row():
    text = build_clarification_request("Labour", "Row 5", "Day Rate")

    assert "Day Rate" in text
    assert "Labour" in text
    assert "Row 5" in text


def test_build_clarification_request_contains_no_numbers():
    """
    A blunt but effective guard: the standard clarification text
    should never contain digits at all, since the only numbers that
    could end up in it are exactly the sensitive ones (benchmark
    rates, group averages, deviation percentages) this function
    exists to keep out - row references are the one legitimate
    exception, and are passed straight through untouched.
    """

    text = build_clarification_request("Labour", "Row 5", "Day Rate")

    # Strip the one legitimate numeric bit (the row reference) before
    # checking for anything else.
    assert text.replace("Row 5", "") == "".join(
        character
        for character in text.replace("Row 5", "")
        if not character.isdigit()
    )
