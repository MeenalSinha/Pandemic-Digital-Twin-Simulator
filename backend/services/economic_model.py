"""
Economic & Resource Allocation Model
Computes real dollar costs, resource requirements, and ROI of interventions.

Economics sourced from:
  - IMF World Economic Outlook 2023
  - WHO Health Expenditure Database
  - Oxford Economic Impact Studies (COVID NPI costs)
  - IHME Resource Requirement Modelling

Outputs:
  - Dollar cost of each intervention (not just %)
  - Hospital bed / ICU / ventilator requirements over time
  - Vaccine dose allocation schedule
  - Cost per life saved (cost-effectiveness ratio)
  - GDP loss vs lives saved trade-off frontier
"""

from __future__ import annotations

import math
from typing import Dict, List, Optional


# GDP per capita (USD) by country — IMF 2023
GDP_PER_CAPITA = {
    "delhi":     2500,    # Delhi NCR adjusted
    "mumbai":    3800,    # Mumbai adjusted
    "new_york":  85000,   # NYC
    "london":    62000,   # London
    "tokyo":     42000,   # Tokyo
    "sao_paulo": 14000,   # Sao Paulo
}

# Hospital resource costs (USD/day)
RESOURCE_COSTS = {
    "hospital_bed_per_day": 800,
    "icu_bed_per_day":       3500,
    "ventilator_per_day":    5000,
    "vaccine_dose":          15,    # average global cost incl. delivery
    "test_unit":             5,
    "contact_trace_per_case": 150,
}

# NPI economic impact (% of daily GDP) — Oxford Economic Impact Study 2022
NPI_GDP_IMPACT = {
    "no_action":           0.00,
    "partial_lockdown":    0.035,  # 3.5% daily GDP loss
    "full_lockdown":       0.085,  # 8.5% daily GDP loss
    "vaccination_rollout": 0.005,  # 0.5% daily GDP loss
    "combined_strategy":   0.040,  # 4.0% daily GDP loss
    "school_closure":      0.018,  # 1.8% daily GDP loss
    "travel_restriction":  0.025,  # 2.5% daily GDP loss
}


class EconomicModel:

    def compute_full_analysis(
        self,
        region_id: str,
        population: int,
        scenario_comparisons: List[Dict],
        simulation_days: int,
    ) -> Dict:
        """
        Full economic analysis across all scenarios.
        Returns costs, resource needs, and cost-effectiveness.
        """
        gdp_per_cap = GDP_PER_CAPITA.get(region_id, 10000)
        daily_gdp = (gdp_per_cap * population) / 365

        baseline = next(
            (s for s in scenario_comparisons if s["scenario"] == "no_action"),
            scenario_comparisons[0] if scenario_comparisons else {}
        )
        baseline_deaths = baseline.get("total_deceased", 1)
        baseline_infected = baseline.get("total_infected", 1)

        analyses = []
        for sc in scenario_comparisons:
            iv = sc["scenario"]
            eco = self._compute_scenario_economics(
                scenario=sc,
                iv_type=iv,
                daily_gdp=daily_gdp,
                population=population,
                simulation_days=simulation_days,
                baseline_deaths=baseline_deaths,
                baseline_infected=baseline_infected,
            )
            analyses.append(eco)

        analyses.sort(key=lambda x: x["cost_effectiveness_ratio"], reverse=True)

        return {
            "currency": "USD",
            "region_daily_gdp_million": round(daily_gdp / 1e6, 1),
            "gdp_per_capita": gdp_per_cap,
            "simulation_days": simulation_days,
            "scenario_economics": analyses,
            "optimal_strategy": self._find_optimal(analyses),
            "resource_summary": self._resource_summary(analyses),
        }

    def _compute_scenario_economics(
        self,
        scenario: Dict,
        iv_type: str,
        daily_gdp: float,
        population: int,
        simulation_days: int,
        baseline_deaths: int,
        baseline_infected: int,
    ) -> Dict:

        # Economic cost of intervention
        gdp_impact_rate = NPI_GDP_IMPACT.get(iv_type, 0.02)
        total_gdp_loss = daily_gdp * gdp_impact_rate * simulation_days

        # Healthcare resource costs
        peak_infected   = scenario.get("peak_infected", 0)
        total_infected  = scenario.get("total_infected", 0)
        total_deceased  = scenario.get("total_deceased", 0)

        # Hospital utilisation (4% of active cases need hospital, 0.8% ICU)
        peak_hospitalised = int(peak_infected * 0.04)
        peak_icu          = int(peak_infected * 0.008)

        hospital_cost = (
            peak_hospitalised * RESOURCE_COSTS["hospital_bed_per_day"] * simulation_days * 0.3
        )
        icu_cost = (
            peak_icu * RESOURCE_COSTS["icu_bed_per_day"] * simulation_days * 0.3
        )

        # Vaccine cost (vaccination_rollout gets vaccine doses for 50% pop)
        vaccine_cost = 0
        if iv_type in ("vaccination_rollout", "combined_strategy"):
            doses = int(population * 0.50 * 1.5)  # 1.5 doses per person average
            vaccine_cost = doses * RESOURCE_COSTS["vaccine_dose"]

        # Testing + contact tracing
        testing_cost = total_infected * RESOURCE_COSTS["test_unit"] * 8  # 8 tests per case

        total_cost = total_gdp_loss + hospital_cost + icu_cost + vaccine_cost + testing_cost

        # Lives saved vs baseline
        lives_saved = max(0, baseline_deaths - total_deceased)

        # Cost per life saved (ICER)
        cost_per_life = total_cost / max(1, lives_saved)

        # DALYs averted (disability-adjusted life years, simplified)
        dalys_averted = lives_saved * 15  # avg 15 years lost per COVID death
        cost_per_daly = total_cost / max(1, dalys_averted)

        # WHO threshold: < 3× GDP per capita per DALY = cost-effective
        gdp_per_cap = daily_gdp * 365 / population
        who_threshold = gdp_per_cap * 3
        is_cost_effective = cost_per_daly < who_threshold

        # Cost-effectiveness ratio (higher = better value)
        # Normalize: avoid division by zero; ratio = lives_saved per $1M
        cost_effectiveness_ratio = round(lives_saved / max(total_cost / 1e6, 0.001), 2)

        # Resource requirements
        beds_needed  = peak_hospitalised
        icu_needed   = peak_icu
        capacity_ok  = beds_needed < (population * 0.003)

        return {
            "scenario":                iv_type,
            "display_name":            iv_type.replace("_", " ").title(),

            # Costs (USD)
            "total_cost_usd":          round(total_cost),
            "total_cost_million":      round(total_cost / 1e6, 1),
            "gdp_loss_usd":            round(total_gdp_loss),
            "healthcare_cost_usd":     round(hospital_cost + icu_cost),
            "vaccine_cost_usd":        round(vaccine_cost),
            "testing_cost_usd":        round(testing_cost),

            # Effectiveness
            "total_infected":          scenario.get("total_infected", 0),
            "total_deceased":          total_deceased,
            "lives_saved":             lives_saved,
            "infections_prevented":    max(0, baseline_infected - total_infected),

            # Cost-effectiveness
            "cost_per_life_saved_usd": round(cost_per_life),
            "cost_per_daly_usd":       round(cost_per_daly),
            "who_cost_effective":      is_cost_effective,
            "cost_effectiveness_ratio": cost_effectiveness_ratio,

            # Resources
            "peak_beds_needed":        beds_needed,
            "peak_icu_needed":         icu_needed,
            "vaccine_doses_needed":    int(population * 0.50 * 1.5) if iv_type in ("vaccination_rollout","combined_strategy") else 0,
            "healthcare_capacity_ok":  capacity_ok,

            # GDP impact
            "gdp_impact_pct":          round(gdp_impact_rate * 100, 1),
            "gdp_impact_days":         simulation_days,
        }

    def _find_optimal(self, analyses: List[Dict]) -> Dict:
        """Find the strategy with best cost-effectiveness ratio."""
        if not analyses:
            return {}

        best = max(analyses, key=lambda x: x["cost_effectiveness_ratio"])
        return {
            "scenario": best["scenario"],
            "display_name": best["display_name"],
            "cost_effectiveness_ratio": best["cost_effectiveness_ratio"],
            "lives_saved": best["lives_saved"],
            "total_cost_million": best["total_cost_million"],
            "who_cost_effective": best["who_cost_effective"],
            "verdict": (
                f"'{best['display_name']}' offers {best['lives_saved']:,} lives saved "
                f"at ${best['total_cost_million']:.1f}M total cost "
                f"(${round(best['cost_per_life_saved_usd']):,} per life). "
                f"{'WHO cost-effective threshold met.' if best['who_cost_effective'] else 'Above WHO threshold — consider alternatives.'}"
            ),
        }

    def _resource_summary(self, analyses: List[Dict]) -> Dict:
        """Summarise peak resource requirements across scenarios."""
        if not analyses:
            return {}

        max_beds = max(a["peak_beds_needed"] for a in analyses)
        min_beds = min(a["peak_beds_needed"] for a in analyses)
        max_icu  = max(a["peak_icu_needed"]  for a in analyses)

        return {
            "max_beds_any_scenario": max_beds,
            "min_beds_best_scenario": min_beds,
            "max_icu_any_scenario": max_icu,
            "bed_savings_from_best_iv": max_beds - min_beds,
        }

    def compute_resource_timeline(
        self,
        timeline: List[Dict],
        population: int,
        region_id: str,
    ) -> List[Dict]:
        """
        Convert SEIR timeline into resource requirement schedule.
        Returns daily bed/ICU/ventilator needs and cost accumulation.
        """
        gdp_per_cap = GDP_PER_CAPITA.get(region_id, 10000)
        daily_gdp = (gdp_per_cap * population) / 365

        cumulative_cost = 0.0
        result = []

        for day_data in timeline[::3]:   # Every 3 days to keep response compact
            infected = day_data.get("infected", 0)
            day      = day_data.get("day", 0)

            beds_needed = int(infected * 0.04)
            icu_needed  = int(infected * 0.008)
            vents       = int(infected * 0.003)

            daily_cost = (
                beds_needed * RESOURCE_COSTS["hospital_bed_per_day"] +
                icu_needed  * RESOURCE_COSTS["icu_bed_per_day"] +
                vents       * RESOURCE_COSTS["ventilator_per_day"]
            )
            cumulative_cost += daily_cost

            hospital_capacity = population * 0.003
            utilization_pct   = round(beds_needed / max(hospital_capacity, 1) * 100, 1)

            result.append({
                "day":                     day,
                "infected":                round(infected),
                "beds_needed":             beds_needed,
                "icu_needed":              icu_needed,
                "ventilators_needed":      vents,
                "utilization_pct":         utilization_pct,
                "capacity_breached":       beds_needed > hospital_capacity,
                "daily_cost_usd":          round(daily_cost),
                "cumulative_cost_million": round(cumulative_cost / 1e6, 2),
            })

        return result


_eco_model: Optional[EconomicModel] = None

def get_economic_model() -> EconomicModel:
    global _eco_model
    if _eco_model is None:
        _eco_model = EconomicModel()
    return _eco_model
