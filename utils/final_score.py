# utils/final_score.py

def compute_final_score(phase1_score, ai_percentage, drift_percentage):
    """
    phase1_score: 0–1
    ai_percentage: 0–100
    drift_percentage: 0–100
    """

    ai_component = 1 - (ai_percentage / 100)
    drift_component = 1 - (drift_percentage / 100)

    final_score = (
        0.5 * phase1_score +
        0.3 * ai_component +
        0.2 * drift_component
    )

    final_score = max(0, min(final_score, 1))

    return round(final_score, 3), round(final_score * 100, 2)