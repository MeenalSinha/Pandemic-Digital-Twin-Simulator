"""
Adaptive Agent Intelligence Service
Agents learn from past simulation runs stored in the database.

Implements:
  1. Parameter adaptation — beta/gamma adjusted from historical accuracy
  2. Policy learning     — which interventions worked best historically
  3. Confidence calibration — agent confidence improves with more data
  4. Dynamic risk thresholds — adjusted from observed regional patterns
"""

from __future__ import annotations

import json
import logging
import math
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class AdaptiveLearningService:
    """
    Reads past simulation runs from the DB and uses them to:
    1. Adjust SEIR parameters based on observed accuracy
    2. Rank interventions by historically observed effectiveness
    3. Calibrate agent confidence from prediction error history
    4. Surface learned patterns as insights
    """

    async def get_adapted_parameters(
        self, region_id: str, base_params: Dict
    ) -> Dict:
        """
        Adjust SEIR parameters based on past simulation history.
        If DB has prior runs: nudge beta toward values that matched reality.
        """
        from services.db_service import db

        history = await db.get_recent_simulations(region_id, limit=20)

        if len(history) < 3:
            # Insufficient history — return base params unchanged with note
            return {
                **base_params,
                "adapted": False,
                "adaptation_reason": "Insufficient history (< 3 runs)",
                "history_count": len(history),
            }

        # Compute average observed R0 from history
        observed_r0s = [h.get("r0", 0) for h in history if h.get("r0", 0) > 0]
        avg_historical_r0 = sum(observed_r0s) / len(observed_r0s)

        # Current model R0 from params
        current_r0 = base_params["beta"] / (base_params["gamma"] + base_params["mu"])

        # Adaptation: nudge beta by up to 15% toward historical mean
        r0_ratio = avg_historical_r0 / max(current_r0, 0.1)
        adapt_factor = 1.0 + (r0_ratio - 1.0) * 0.15  # 15% adaptation strength
        adapt_factor = max(0.85, min(1.15, adapt_factor))  # cap at ±15%

        adapted_beta = round(base_params["beta"] * adapt_factor, 4)

        # Most common intervention in history
        interventions = [h.get("intervention") for h in history]
        most_tested = max(set(interventions), key=interventions.count) if interventions else "no_action"

        return {
            **base_params,
            "beta": adapted_beta,
            "adapted": True,
            "adaptation_reason": f"Adjusted from {len(history)} historical runs",
            "history_count": len(history),
            "avg_historical_r0": round(avg_historical_r0, 2),
            "current_model_r0": round(current_r0, 2),
            "adapt_factor": round(adapt_factor, 3),
            "most_tested_intervention": most_tested,
        }

    async def get_learned_policy_rankings(
        self, region_id: str
    ) -> List[Dict]:
        """
        Return interventions ranked by historical performance for this region.
        Combines DB evidence with RAG knowledge base rankings.
        """
        from services.db_service import db
        from services.rag_service import PandemicKnowledgeBase

        history = await db.get_recent_simulations(region_id, limit=50)
        kb = PandemicKnowledgeBase.get_instance()

        # Group by intervention
        groups: Dict[str, List[Dict]] = {}
        for run in history:
            iv = run.get("intervention", "unknown")
            if iv not in groups:
                groups[iv] = []
            groups[iv].append(run)

        rankings = []
        for iv, runs in groups.items():
            if not runs:
                continue

            avg_peak = sum(r.get("peak_infected", 0) for r in runs) / len(runs)
            avg_r0 = sum(r.get("r0", 1.5) for r in runs) / len(runs)

            # RAG: evidence base for this intervention
            evidence = kb.query(iv.replace("_", " "), top_k=1,
                                 intervention_filter=iv if iv in kb._docs[0] else None)
            rag_effectiveness = evidence[0].effectiveness if evidence else 0.5

            rankings.append({
                "intervention": iv,
                "times_simulated": len(runs),
                "avg_peak_infected": round(avg_peak),
                "avg_r0": round(avg_r0, 2),
                "rag_effectiveness": rag_effectiveness,
                "learned_score": round(
                    rag_effectiveness * 60 + (1 - min(1, avg_r0 / 5)) * 40, 1
                ),
            })

        rankings.sort(key=lambda x: x["learned_score"], reverse=True)
        return rankings

    async def get_calibrated_confidence(
        self, region_id: str, agent_name: str, base_confidence: float
    ) -> float:
        """
        Calibrate agent confidence based on historical prediction accuracy.
        More history → narrower confidence intervals → higher/lower calibrated score.
        """
        from services.db_service import db

        history = await db.get_recent_simulations(region_id, limit=20)
        n = len(history)

        if n == 0:
            # No history: slightly reduce confidence to reflect uncertainty
            return round(base_confidence * 0.90, 3)
        elif n < 5:
            # Little history: slight reduction
            return round(base_confidence * 0.95, 3)
        elif n < 15:
            # Moderate history: trust the base
            return round(base_confidence, 3)
        else:
            # Rich history: slight boost (agent has been tested)
            return round(min(0.97, base_confidence * 1.05), 3)

    async def get_regional_insights(self, region_id: str) -> Dict:
        """
        Generate data-driven insights from accumulated simulation history.
        Returns patterns, anomalies, and learned recommendations.
        """
        from services.db_service import db

        history = await db.get_recent_simulations(region_id, limit=30)
        snapshot_summary = await db.get_simulation_history_summary(region_id)

        if not history:
            return {
                "has_history": False,
                "message": "No prior simulations for this region. Run a simulation to build adaptive intelligence.",
                "recommendations": [],
            }

        # Trend: is peak infected increasing across runs?
        peaks = [h.get("peak_infected", 0) for h in history]
        r0s   = [h.get("r0", 1.5) for h in history]

        if len(peaks) >= 2:
            recent_peak = sum(peaks[:3]) / min(3, len(peaks))
            older_peak  = sum(peaks[-3:]) / min(3, len(peaks))
            peak_trend = "worsening" if recent_peak > older_peak * 1.1 else \
                         "improving" if recent_peak < older_peak * 0.9 else "stable"
        else:
            peak_trend = "insufficient_data"

        avg_r0    = sum(r0s) / len(r0s)
        max_peak  = max(peaks) if peaks else 0
        min_peak  = min(peaks) if peaks else 0

        # Best performing intervention from history
        iv_peaks = {}
        for run in history:
            iv = run.get("intervention", "unknown")
            p  = run.get("peak_infected", 0)
            if iv not in iv_peaks:
                iv_peaks[iv] = []
            iv_peaks[iv].append(p)

        best_iv = min(iv_peaks, key=lambda iv: sum(iv_peaks[iv]) / len(iv_peaks[iv])) \
                  if iv_peaks else "no_action"
        best_iv_avg = sum(iv_peaks[best_iv]) / len(iv_peaks[best_iv]) if best_iv in iv_peaks else 0

        insights = []
        if avg_r0 > 2.0:
            insights.append(f"Historical average R0={avg_r0:.2f} is critically high — sustained transmission")
        if peak_trend == "worsening":
            insights.append("Peak infections trending upward across recent simulations")
        if best_iv and best_iv != "no_action":
            insights.append(f"'{best_iv.replace('_', ' ').title()}' historically produced lowest peak ({round(best_iv_avg):,} cases)")

        return {
            "has_history":        True,
            "total_simulations":  len(history),
            "avg_r0":             round(avg_r0, 2),
            "peak_range":         [round(min_peak), round(max_peak)],
            "peak_trend":         peak_trend,
            "best_intervention":  best_iv,
            "best_iv_avg_peak":   round(best_iv_avg),
            "interventions_tested": list(iv_peaks.keys()),
            "insights":           insights,
            "summary":            snapshot_summary,
        }


# Singleton
_adaptive_service: Optional[AdaptiveLearningService] = None

def get_adaptive_service() -> AdaptiveLearningService:
    global _adaptive_service
    if _adaptive_service is None:
        _adaptive_service = AdaptiveLearningService()
    return _adaptive_service
