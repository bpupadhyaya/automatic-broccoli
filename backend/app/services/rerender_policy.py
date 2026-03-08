from __future__ import annotations


def decide_qc_action(overall_score: float) -> str:
    if overall_score >= 0.82:
        return "approved"
    if overall_score >= 0.60:
        return "rerender"
    return "manual_review"
