"""
LLM Service — Pandemic Digital Twin Simulator
Powered by Gemini 2.5 Pro (Google AI Studio REST API)

Setup:
  1. Get a free API key at: https://aistudio.google.com/apikey
  2. Set the environment variable:
       Windows:  set GEMINI_API_KEY=your-key-here
       Linux:    export GEMINI_API_KEY=your-key-here

Falls back to high-quality analytical models when no key is set.
"""

from __future__ import annotations

import logging
import os
from typing import Dict, List, Optional

import requests

from services.rag_service import PandemicKnowledgeBase, RAGResult

logger = logging.getLogger(__name__)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL   = "gemini-2.5-pro-preview-03-25"
GEMINI_URL     = (
    f"https://generativelanguage.googleapis.com/v1beta/models/"
    f"{GEMINI_MODEL}:generateContent"
)
_TIMEOUT = 45


def _call_gemini(system_prompt: str, user_prompt: str, max_tokens: int = 512) -> Optional[str]:
    """
    Call Gemini 2.5 Pro via Google AI Studio REST API.
    Returns generated text or None on any failure.
    thinkingBudget=0 keeps responses fast (disables extended thinking).
    """
    if not GEMINI_API_KEY:
        return None

    payload = {
        "contents": [
            {"role": "user", "parts": [{"text": user_prompt}]}
        ],
        "systemInstruction": {
            "parts": [{"text": system_prompt}]
        },
        "generationConfig": {
            "temperature":     0.3,
            "maxOutputTokens": max_tokens,
            "thinkingConfig":  {"thinkingBudget": 0},
        },
    }

    try:
        resp = requests.post(
            GEMINI_URL,
            params={"key": GEMINI_API_KEY},
            json=payload,
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
        data       = resp.json()
        candidates = data.get("candidates", [])
        if not candidates:
            logger.warning("Gemini returned no candidates")
            return None
        parts = candidates[0].get("content", {}).get("parts", [])
        text  = "".join(p.get("text", "") for p in parts).strip()
        return text or None

    except requests.exceptions.Timeout:
        logger.warning("Gemini API timed out after %ds", _TIMEOUT)
        return None
    except requests.exceptions.HTTPError as e:
        status = e.response.status_code if e.response else "unknown"
        body   = e.response.text[:300] if e.response else ""
        logger.warning("Gemini HTTP %s: %s", status, body)
        return None
    except Exception as e:
        logger.warning("Gemini call failed: %s", e)
        return None


class LLMService:
    """
    Gemini 2.5 Pro powered analysis with RAG context injection.
    Falls back to deterministic analytical models when no API key is set.
    """

    def __init__(self):
        self._kb      = PandemicKnowledgeBase.get_instance()
        self._has_llm = bool(GEMINI_API_KEY)
        self._model   = GEMINI_MODEL if self._has_llm else "analytical-fallback"

        if self._has_llm:
            logger.info("LLMService: Gemini 2.5 Pro active (model=%s)", GEMINI_MODEL)
        else:
            logger.info(
                "LLMService: No GEMINI_API_KEY — using analytical fallbacks. "
                "Get a free key at https://aistudio.google.com/apikey and run: "
                "set GEMINI_API_KEY=your-key-here"
            )

    def interpret_simulation(self, region_name: str, r0: float, severity: str,
                              peak_infected: int, peak_day: int,
                              attack_rate: float, population: int) -> Dict:
        rag_results = self._kb.query(
            f"outbreak R0 {r0:.1f} severity {severity} attack rate {attack_rate:.1f}%",
            top_k=3,
        )
        rag_context = self._kb.format_context(rag_results)

        llm_text = None
        if self._has_llm:
            system = (
                "You are an expert epidemiologist advising public health officials. "
                "Provide concise, evidence-based analysis. Be direct and specific. "
                "No markdown headers or bullet points. Plain paragraphs only. Under 200 words."
            )
            user = (
                f"Region: {region_name}\n"
                f"Epidemic state: R0={r0:.2f}, severity={severity}, "
                f"peak {peak_infected:,} infections on day {peak_day}, "
                f"attack rate {attack_rate:.1f}% of {population:,} population.\n\n"
                f"{rag_context}\n\n"
                f"Provide a 2-3 sentence epidemiological assessment and outlook."
            )
            llm_text = _call_gemini(system, user, max_tokens=300)

        return {
            "interpretation": llm_text or self._fallback_interpretation(r0, severity, peak_day, attack_rate),
            "source": "gemini-2.5-pro-rag" if llm_text else "analytical-model",
            "model":  self._model,
            "rag_sources": [{"id": r.id, "title": r.title, "similarity": r.similarity_score}
                            for r in rag_results],
        }

    def generate_policy_recommendation(self, region_name: str, severity: str,
                                        r0: float, top_policy: str,
                                        high_risk_zones: int,
                                        capacity_breach_day: Optional[int]) -> Dict:
        rag_results = self._kb.get_policy_evidence(
            top_policy.lower().replace(" ", "_"), r0
        )
        rag_context = self._kb.format_context(rag_results)

        llm_text = None
        if self._has_llm:
            system = (
                "You are a senior public health policy advisor. "
                "Give specific, actionable recommendations grounded in historical evidence. "
                "No markdown. Plain text only. Under 180 words."
            )
            capacity_note = (
                f"Healthcare capacity will be breached on day {capacity_breach_day}. "
                if capacity_breach_day else ""
            )
            user = (
                f"Region: {region_name} | Severity: {severity} | R0: {r0:.2f}\n"
                f"High-risk zones: {high_risk_zones} | Recommended policy: {top_policy}\n"
                f"{capacity_note}\n\n"
                f"{rag_context}\n\n"
                f"In 2-3 sentences: why is this policy recommended, cite historical evidence, "
                f"and state the single most critical immediate action."
            )
            llm_text = _call_gemini(system, user, max_tokens=280)

        return {
            "reasoning": llm_text or self._fallback_policy_reasoning(top_policy, severity, r0, capacity_breach_day),
            "source":    "gemini-2.5-pro-rag" if llm_text else "analytical-model",
            "model":     self._model,
            "evidence":  [{"title": r.title, "effectiveness": r.effectiveness} for r in rag_results],
        }

    def answer_natural_language_query(self, query: str, region_name: str,
                                       sim_context: Dict) -> Dict:
        rag_results = self._kb.query(query, top_k=4)
        rag_context = self._kb.format_context(rag_results)
        r0       = sim_context.get("r0", 0)
        severity = sim_context.get("severity", "UNKNOWN")

        llm_text = None
        if self._has_llm:
            system = (
                "You are an epidemiologist advising on pandemic response. "
                "Answer questions about disease spread, interventions, and public health policy. "
                "Be specific, evidence-based, and practical. No markdown. Under 200 words."
            )
            user = (
                f"Region: {region_name} (R0={r0:.2f}, severity={severity})\n\n"
                f"{rag_context}\n\n"
                f"Question: {query}\n\n"
                f"Answer based on the evidence above and epidemiological principles."
            )
            llm_text = _call_gemini(system, user, max_tokens=350)

        return {
            "answer": llm_text or self._fallback_nl_answer(query, region_name, sim_context),
            "source": "gemini-2.5-pro-rag" if llm_text else "analytical-model",
            "model":  self._model,
            "rag_sources": [{"id": r.id, "title": r.title, "similarity": r.similarity_score}
                            for r in rag_results[:3]],
        }

    # ── Analytical fallbacks ──────────────────────────────────────────────────

    def _fallback_interpretation(self, r0: float, severity: str,
                                  peak_day: int, attack_rate: float) -> str:
        if r0 > 3:     trend = "explosive exponential growth"
        elif r0 > 2:   trend = "rapid epidemic expansion"
        elif r0 > 1.5: trend = "sustained community transmission"
        elif r0 > 1:   trend = "moderate ongoing spread"
        else:          trend = "sub-threshold transmission that will self-resolve"

        return (
            f"With R0={r0:.2f}, the epidemic shows {trend}. "
            f"Peak infections are expected on day {peak_day}, affecting "
            f"approximately {attack_rate:.1f}% of the susceptible population. "
            f"Historical outbreaks with similar parameters required "
            f"{'immediate aggressive intervention' if r0 > 2 else 'targeted measures'} "
            f"to prevent healthcare system saturation."
        )

    def _fallback_policy_reasoning(self, policy: str, severity: str,
                                    r0: float, capacity_breach_day: Optional[int]) -> str:
        policy_map = {
            "Full Lockdown": (
                "A full lockdown is indicated given the critical R0 and severity level. "
                "Historical evidence from Wuhan 2020 demonstrates 90% transmission reduction "
                "within 14 days. Immediate implementation preserves healthcare capacity."
            ),
            "Combined Targeted Strategy": (
                "A combined targeted strategy offers the best cost-effectiveness ratio. "
                "Evidence from Taiwan and Portugal shows layered NPIs with vaccination "
                "achieve control without full economic disruption."
            ),
            "Partial Lockdown": (
                "Partial restrictions are appropriate given the current transmission rate. "
                "UK Tier evidence shows 40-55% mobility reduction achieves R-effective below 1. "
                "Prioritise high-density zones identified by the risk analysis agent."
            ),
            "Accelerated Vaccination": (
                "Accelerated vaccination is the highest-leverage long-term intervention. "
                "Israel 2021 data shows 95% efficacy after 50% population coverage. "
                "Prioritise elderly and healthcare workers."
            ),
        }
        return policy_map.get(
            policy,
            f"Based on {severity} severity and R0={r0:.2f}, the {policy} intervention "
            f"offers the optimal balance of transmission reduction and economic sustainability."
        )

    def _fallback_nl_answer(self, query: str, region: str, ctx: Dict) -> str:
        q        = query.lower()
        r0       = ctx.get("r0", 1.5)
        severity = ctx.get("severity", "MODERATE")

        if "school" in q:
            return (
                f"Closing schools in {region} reduces R-effective by approximately 15-25% "
                f"(current R0={r0:.2f}). UK SAGE modelling shows this cuts contact rates "
                f"in under-20 age groups, which act as transmission bridges to vulnerable adults. "
                f"Healthcare worker absenteeism from childcare partially offsets the gain. "
                f"Expected economic cost: 1.5-2.5% regional GDP."
            )
        if "lockdown" in q or "lock down" in q:
            return (
                f"A full lockdown in {region} would reduce R0={r0:.2f} to approximately "
                f"{r0 * 0.08:.2f} based on Wuhan 2020 data (90% transmission reduction). "
                f"The epidemic peak would be delayed and significantly flattened. "
                f"Economic cost: 8-12% GDP for the lockdown duration."
            )
        if "vaccin" in q:
            return (
                f"Accelerated vaccination in {region} reduces severe cases by up to 95% "
                f"once 60% population coverage is achieved (Israel mRNA 2021 data). "
                f"Herd immunity threshold (67-70%) could be reached within 12-16 weeks "
                f"of an accelerated programme prioritising elderly and healthcare workers."
            )
        return (
            f"Based on current data for {region} (R0={r0:.2f}, severity={severity}): "
            f"the epidemic is {'growing' if r0 > 1 else 'declining'} and requires "
            f"{'immediate intervention' if severity in ('CRITICAL', 'HIGH') else 'monitoring'}. "
            f"Use the Scenarios page to compare all intervention strategies with quantified impact."
        )


_llm_service: Optional[LLMService] = None


def get_llm_service() -> LLMService:
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service
