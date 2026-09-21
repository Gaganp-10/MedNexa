"""
Recovery Score Calculation Service.

MEDICAL SAFETY NOTICE:
This calculation is a prototype heuristic for decision-support purposes only.
It is not clinically validated and does not replace medical judgment.
"""


def calculate_recovery_score(log, wound_result):
    """
    Calculates a prototype recovery score (0 to 100) based on self-reported
    vitals, medication status, and prototype wound redness analysis.
    """
    if log is None:
        return 100

    score = 100

    # Elevated temperature indicator penalty
    if log.temperature is not None and log.temperature > 38.0:
        score -= 20

    # High pain level indicator penalty
    if log.pain_level is not None and log.pain_level > 7:
        score -= 20

    # Unrecorded medication adherence penalty
    if not log.medication_taken:
        score -= 15

    # Visual wound concern indicator penalty (supports new phrasing & legacy data)
    wound_text = (wound_result or "").lower()
    if "concern" in wound_text or "infection" in wound_text:
        score -= 25

    if score < 0:
        score = 0
    elif score > 100:
        score = 100

    return score