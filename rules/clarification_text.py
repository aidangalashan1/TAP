# rules/clarification_text.py


def build_clarification_request(worksheet_name, record_reference, field_name):
    """
    The standard, supplier-facing clarification request text used
    across every kind of finding (blanks/zeroes/duplicates/outliers,
    benchmark comparison, between-response comparison).

    Deliberately generic: it only ever names which field/row/sheet
    needs a response, never any number derived from the comparison
    itself - no benchmark rate, no other supplier's value, no
    computed average/median/Z-score/IQR bound. Those are exactly the
    kind of commercially sensitive figures that must never leave the
    buyer's own report. The full detail (including any such figures)
    belongs in Finding.reason instead, which is for the internal
    report only and is never meant to be copied out to a supplier.

    Keeping this the single place clarification text is built means
    no future check can accidentally leak comparator data into it by
    just formatting `reason` into the clarification, the way earlier
    versions of this code did.
    """

    return (
        "Clarification required: please confirm and, if necessary, "
        f"provide justification for the value submitted for "
        f"'{field_name}' on the '{worksheet_name}' worksheet "
        f"({record_reference})."
    )
