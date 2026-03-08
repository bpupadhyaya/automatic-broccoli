from __future__ import annotations


class RerenderPolicyService:
    """Apply acceptance thresholds to QC scores."""

    def decide(self, qc_result: dict) -> str:
        overall_score = float(qc_result.get("overall_score", 0.0))
        if overall_score >= 0.82:
            return "approved"
        if overall_score >= 0.60:
            return "rerender"
        return "manual_review"


def decide_qc_action(overall_score: float) -> str:
    return RerenderPolicyService().decide({"overall_score": overall_score})
