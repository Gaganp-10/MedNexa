"""
Patient Risk Assessment Service.

MEDICAL SAFETY NOTICE:
This module provides prototype decision-support indicators, NOT medical diagnoses.
These indicators are rule-based heuristics and are not clinically validated.
Any potential risk indicator should be reviewed by licensed medical professionals.
"""


def predict_patient_risk(log, wound_result):
    """
    Evaluates rule-based prototype risk indicators for a patient.
    
    Handles empty states gracefully where no logs or wound analyses exist.
    """
    if log is None:
        return "Insufficient data for risk assessment (prototype indicator)"

    wound_text = (wound_result or "").lower()
    has_wound_concern = "concern" in wound_text or "infection" in wound_text

    temp = getattr(log, "temperature", None)
    pain = getattr(log, "pain_level", None)

    if temp is not None and temp > 38.0 and has_wound_concern:
        return "Potential elevated risk: elevated temperature and visual wound concern; clinical review recommended (prototype indicator)"

    if pain is not None and pain > 8:
        return "Potential moderate risk: high pain reported; medical review may be appropriate (prototype indicator)"

    return "Routine observation recommended: low risk indicators (prototype indicator)"