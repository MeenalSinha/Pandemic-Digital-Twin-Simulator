"""
RAG Knowledge Base — Pandemic Digital Twin Simulator
Stores past pandemic data, policy effectiveness research, and intervention
summaries as TF-IDF + FAISS vector embeddings.

Uses no external embedding API — embeddings are computed locally using
a deterministic TF-IDF vectoriser over the knowledge corpus.

On first call, the index is built in memory (< 1 second).
"""

from __future__ import annotations

import math
import re
import logging
import time
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional
import numpy as np

logger = logging.getLogger(__name__)


# ── Knowledge corpus ──────────────────────────────────────────────────────────
# Each entry represents a research finding or policy record.
# Sources: WHO technical briefs, Lancet/NEJM studies, Oxford OxCGRT dataset.

PANDEMIC_KNOWLEDGE_BASE: List[Dict] = [
    # ── Lockdown effectiveness ─────────────────────────────────────────────
    {
        "id": "npi_001",
        "title": "Full lockdown effectiveness — Wuhan 2020",
        "content": (
            "The Wuhan full lockdown (Jan–Apr 2020) reduced the effective reproduction number "
            "from 3.86 to 0.32 within 14 days. Transmission fell by 90% during strict "
            "movement restrictions. Healthcare capacity was preserved. Economic cost was "
            "estimated at 8–12% GDP contraction for the affected period."
        ),
        "tags": ["lockdown", "full_lockdown", "wuhan", "china", "R0", "effectiveness"],
        "intervention": "full_lockdown",
        "effectiveness": 0.90,
        "economic_cost": 0.90,
    },
    {
        "id": "npi_002",
        "title": "Partial lockdown — UK Tier system 2020",
        "content": (
            "The UK tiered restriction system reduced mobility by 40–55% in affected regions. "
            "R-effective fell from 1.4 to approximately 0.85 in Tier 3 areas. "
            "Economic impact was 4–6% GDP. Business closures and hospitality restrictions "
            "were the primary transmission reduction mechanisms."
        ),
        "tags": ["partial_lockdown", "uk", "tiered", "R0", "mobility"],
        "intervention": "partial_lockdown",
        "effectiveness": 0.50,
        "economic_cost": 0.55,
    },
    # ── Vaccination effectiveness ──────────────────────────────────────────
    {
        "id": "vacc_001",
        "title": "mRNA vaccine effectiveness — Israel 2021",
        "content": (
            "Israel's rapid BNT162b2 mRNA vaccination campaign achieved 95% efficacy against "
            "symptomatic COVID-19. After 60% population coverage, severe cases dropped 98%. "
            "Hospital admissions fell by 90% within 3 weeks of achieving 50% coverage. "
            "Herd immunity threshold estimated at 67–70% for original strain."
        ),
        "tags": ["vaccination", "vaccine", "mRNA", "israel", "herd_immunity", "efficacy"],
        "intervention": "vaccination_rollout",
        "effectiveness": 0.75,
        "economic_cost": 0.10,
    },
    {
        "id": "vacc_002",
        "title": "Vaccination rollout speed — South Korea 2021",
        "content": (
            "South Korea's phased vaccination rollout prioritising elderly and healthcare "
            "workers reduced mortality by 80% before achieving population-wide coverage. "
            "Contact tracing alongside vaccination proved synergistic, allowing R-effective "
            "to remain below 1.0 throughout the rollout period. Economic cost minimal."
        ),
        "tags": ["vaccination", "south_korea", "phased", "elderly", "contact_tracing"],
        "intervention": "vaccination_rollout",
        "effectiveness": 0.70,
        "economic_cost": 0.12,
    },
    # ── School closures ────────────────────────────────────────────────────
    {
        "id": "school_001",
        "title": "School closure impact — SAGE modelling 2020",
        "content": (
            "UK SAGE modelling estimated school closures reduce R-effective by 15–25%. "
            "The primary mechanism is reduced contact rates in under-20 age groups, which "
            "act as transmission bridges to vulnerable adults. However, healthcare worker "
            "absenteeism due to childcare needs partially offsets gains. "
            "Economic and social cost is significant: estimated 1.5–2.5% GDP."
        ),
        "tags": ["school_closure", "schools", "education", "children", "UK", "SAGE"],
        "intervention": "school_closure",
        "effectiveness": 0.25,
        "economic_cost": 0.20,
    },
    # ── Travel restrictions ────────────────────────────────────────────────
    {
        "id": "travel_001",
        "title": "Travel restrictions — New Zealand 2020",
        "content": (
            "New Zealand's border closure (March 2020) prevented importation of new strains "
            "for 18 months. Combined with strict managed isolation, the measure reduced "
            "community transmission to near-zero. However, it required 100% quarantine "
            "compliance and was only feasible due to island geography. "
            "Economic cost: 4–5% GDP from tourism loss."
        ),
        "tags": ["travel", "border", "new_zealand", "island", "importation", "quarantine"],
        "intervention": "travel_restriction",
        "effectiveness": 0.35,
        "economic_cost": 0.40,
    },
    # ── Combined strategies ────────────────────────────────────────────────
    {
        "id": "combined_001",
        "title": "Layered NPI strategy — Taiwan 2020–2021",
        "content": (
            "Taiwan deployed a layered strategy: mask mandates, contact tracing, "
            "targeted quarantine, and targeted business restrictions without full lockdown. "
            "R-effective remained below 1.0 for 18 months with fewer than 1,000 total cases. "
            "Economic growth remained positive (3.1% in 2020) — the only major economy "
            "to avoid recession while controlling transmission effectively."
        ),
        "tags": ["combined", "layered", "taiwan", "masks", "contact_tracing", "targeted"],
        "intervention": "combined_strategy",
        "effectiveness": 0.82,
        "economic_cost": 0.20,
    },
    {
        "id": "combined_002",
        "title": "Targeted zone-based restrictions — Germany 2020",
        "content": (
            "Germany's county-level (Landkreis) incidence thresholds triggered automatic "
            "restrictions at 50 and 200 cases per 100,000. This targeted approach reduced "
            "national transmission while preserving economic activity in low-incidence areas. "
            "The approach is most effective when data infrastructure allows rapid case "
            "detection and public compliance is high (>80%)."
        ),
        "tags": ["targeted", "zone", "germany", "incidence", "thresholds", "county"],
        "intervention": "combined_strategy",
        "effectiveness": 0.68,
        "economic_cost": 0.40,
    },
    # ── High density scenarios ─────────────────────────────────────────────
    {
        "id": "density_001",
        "title": "High density transmission — Mumbai Dharavi 2020",
        "content": (
            "Dharavi (Mumbai), with 82,000 people/km², achieved outbreak control through "
            "intensive contact tracing, fever camps, and targeted micro-containment. "
            "Despite extreme density, R-effective was reduced from 2.6 to 0.9 in 6 weeks. "
            "Key insight: in ultra-high density areas, targeted micro-containment outperforms "
            "broad lockdowns, as full lockdown compliance is impossible."
        ),
        "tags": ["density", "dharavi", "mumbai", "india", "slum", "micro_containment"],
        "intervention": "combined_strategy",
        "effectiveness": 0.70,
        "economic_cost": 0.25,
    },
    # ── Healthcare capacity ────────────────────────────────────────────────
    {
        "id": "health_001",
        "title": "Healthcare surge capacity — Italy 2020",
        "content": (
            "Italy's Lombardy region was overwhelmed with an ICU occupancy exceeding 200% "
            "in March 2020, requiring field hospitals and military assistance. "
            "The critical threshold was reached at 0.5% active case prevalence. "
            "Pre-emptive intervention 2 weeks earlier would have prevented ICU overflow. "
            "Lesson: act when R0 > 1.5 and cases double-time < 10 days."
        ),
        "tags": ["healthcare", "ICU", "capacity", "italy", "surge", "overwhelmed"],
        "intervention": "full_lockdown",
        "effectiveness": 0.85,
        "economic_cost": 0.80,
    },
    # ── Vaccination + partial lockdown synergy ─────────────────────────────
    {
        "id": "synergy_001",
        "title": "Vaccination + NPI synergy — Portugal 2021",
        "content": (
            "Portugal combined rapid vaccination (80% coverage by Aug 2021) with "
            "targeted nighttime curfews. The synergistic effect reduced R-effective more "
            "than either measure alone. Vaccination reduced severity; NPIs reduced "
            "transmission during the critical vaccination window. "
            "This combined strategy is the most cost-effective in the medium term."
        ),
        "tags": ["vaccination", "partial_lockdown", "combined", "portugal", "synergy", "curfew"],
        "intervention": "combined_strategy",
        "effectiveness": 0.80,
        "economic_cost": 0.35,
    },
    # ── R0 by disease ──────────────────────────────────────────────────────
    {
        "id": "r0_001",
        "title": "Reproduction numbers by pathogen — WHO 2022",
        "content": (
            "Basic reproduction numbers (R0) by pathogen: "
            "COVID-19 original: 2.5–3.5; Delta variant: 5–6; Omicron: 8–15; "
            "Seasonal influenza: 1.2–1.4; SARS 2003: 2–5; Measles: 12–18. "
            "Interventions must reduce R-effective below 1.0 to end an outbreak. "
            "Required transmission reduction = 1 - (1/R0)."
        ),
        "tags": ["R0", "reproduction_number", "COVID", "influenza", "measles", "WHO"],
        "intervention": "no_action",
        "effectiveness": 0.0,
        "economic_cost": 0.0,
    },
    # ── Early action advantage ─────────────────────────────────────────────
    {
        "id": "timing_001",
        "title": "Early intervention advantage — modelling meta-analysis 2021",
        "content": (
            "A meta-analysis of 35 outbreak responses found that interventions implemented "
            "within 7 days of R-effective exceeding 1.5 required 40% less economic disruption "
            "to achieve control compared to delayed responses. "
            "Each week of delay roughly doubled the total case burden. "
            "Early action is the highest-leverage public health intervention."
        ),
        "tags": ["timing", "early", "intervention", "delay", "economic", "meta-analysis"],
        "intervention": "combined_strategy",
        "effectiveness": 0.75,
        "economic_cost": 0.30,
    },
]


@dataclass
class RAGResult:
    """A single retrieval result from the knowledge base."""
    id: str
    title: str
    content: str
    tags: List[str]
    intervention: str
    effectiveness: float
    economic_cost: float
    similarity_score: float


class TFIDFEmbedder:
    """
    Lightweight TF-IDF vectoriser.
    Produces deterministic, reproducible vectors with no external dependencies.
    """

    def __init__(self, corpus: List[str]):
        self._vocab: Dict[str, int] = {}
        self._idf: np.ndarray = np.array([])
        self._fit(corpus)

    def _tokenise(self, text: str) -> List[str]:
        text = text.lower()
        text = re.sub(r"[^a-z0-9 ]", " ", text)
        return [t for t in text.split() if len(t) > 2]

    def _fit(self, corpus: List[str]) -> None:
        df: Dict[str, int] = {}
        tokenised = [self._tokenise(doc) for doc in corpus]
        all_terms: set = set()
        for tokens in tokenised:
            all_terms.update(tokens)

        self._vocab = {term: i for i, term in enumerate(sorted(all_terms))}
        V = len(self._vocab)
        N = len(corpus)

        for tokens in tokenised:
            for term in set(tokens):
                if term in self._vocab:
                    df[term] = df.get(term, 0) + 1

        self._idf = np.zeros(V)
        for term, idx in self._vocab.items():
            self._idf[idx] = math.log((N + 1) / (df.get(term, 0) + 1)) + 1

    def embed(self, text: str) -> np.ndarray:
        tokens = self._tokenise(text)
        V = len(self._vocab)
        tf = np.zeros(V)
        for token in tokens:
            if token in self._vocab:
                tf[self._vocab[token]] += 1
        if tokens:
            tf /= len(tokens)
        vec = tf * self._idf
        norm = np.linalg.norm(vec)
        return (vec / norm).astype(np.float32) if norm > 0 else vec.astype(np.float32)


class PandemicKnowledgeBase:
    """
    FAISS-backed vector knowledge base for pandemic policy retrieval.
    Implements RAG (Retrieval-Augmented Generation) over the knowledge corpus.
    """

    _instance: Optional["PandemicKnowledgeBase"] = None

    def __init__(self):
        import faiss  # type: ignore

        self._docs = PANDEMIC_KNOWLEDGE_BASE
        corpus_texts = [
            f"{d['title']} {d['content']} {' '.join(d['tags'])}"
            for d in self._docs
        ]

        self._embedder = TFIDFEmbedder(corpus_texts)
        vectors = np.vstack([self._embedder.embed(t) for t in corpus_texts])
        dim = vectors.shape[1]

        self._index = faiss.IndexFlatIP(dim)   # inner-product (cosine on unit vecs)
        self._index.add(vectors)

        logger.info("PandemicKnowledgeBase ready: %d documents, dim=%d", len(self._docs), dim)

    @classmethod
    def get_instance(cls) -> "PandemicKnowledgeBase":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def query(self, query_text: str, top_k: int = 3,
              intervention_filter: Optional[str] = None) -> List[RAGResult]:
        """
        Retrieve the top-k most relevant knowledge base entries for a query.
        Optionally filter by intervention type.
        """
        vec = self._embedder.embed(query_text).reshape(1, -1)
        k = min(top_k * 3, len(self._docs))
        distances, indices = self._index.search(vec, k)

        results: List[RAGResult] = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx < 0:
                continue
            doc = self._docs[idx]
            if intervention_filter and doc["intervention"] != intervention_filter:
                continue
            results.append(RAGResult(
                id=doc["id"],
                title=doc["title"],
                content=doc["content"],
                tags=doc["tags"],
                intervention=doc["intervention"],
                effectiveness=doc["effectiveness"],
                economic_cost=doc["economic_cost"],
                similarity_score=round(float(dist), 4),
            ))
            if len(results) >= top_k:
                break

        return results

    def get_similar_outbreaks(self, r0: float, severity: str,
                               region_density: int) -> List[RAGResult]:
        """
        Find historical outbreaks with similar epidemiological parameters.
        """
        query = (
            f"outbreak R0 {r0:.1f} severity {severity} "
            f"density {region_density} intervention strategy effectiveness"
        )
        return self.query(query, top_k=3)

    def get_policy_evidence(self, intervention: str, r0: float) -> List[RAGResult]:
        """
        Retrieve evidence-based policy data for a specific intervention.
        """
        query = (
            f"{intervention.replace('_', ' ')} policy effectiveness R0 {r0:.1f} "
            f"transmission reduction economic cost"
        )
        return self.query(query, top_k=3, intervention_filter=intervention)

    def format_context(self, results: List[RAGResult]) -> str:
        """
        Format retrieved documents as a context string for LLM prompting.
        """
        if not results:
            return "No relevant historical data found."
        lines = ["Relevant historical evidence:"]
        for i, r in enumerate(results, 1):
            lines.append(
                f"\n[{i}] {r.title} (similarity: {r.similarity_score:.2f})\n"
                f"    {r.content[:300]}..."
            )
        return "\n".join(lines)
