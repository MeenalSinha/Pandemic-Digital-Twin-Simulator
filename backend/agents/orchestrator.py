"""
Multi-Agent Orchestration System
Coordinates Prediction, Risk Analysis, Policy Recommendation, and Simulation Agents
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum
import json
import time

logger = logging.getLogger(__name__)


class AgentStatus(Enum):
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class AgentMessage:
    """Message passed between agents"""
    sender: str
    receiver: str
    content: Dict[str, Any]
    timestamp: float = field(default_factory=time.time)
    message_id: str = ""
    
    def __post_init__(self):
        if not self.message_id:
            self.message_id = f"{self.sender}_{int(self.timestamp)}"


@dataclass  
class AgentResult:
    """Result from an agent's analysis"""
    agent_name: str
    status: AgentStatus
    output: Dict[str, Any]
    reasoning: str
    confidence: float
    execution_time: float
    recommendations: List[str] = field(default_factory=list)


class BaseAgent:
    """Base class for all agents"""
    
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.status = AgentStatus.IDLE
        self.message_queue: List[AgentMessage] = []
        self.results: List[AgentResult] = []
    
    def receive_message(self, message: AgentMessage):
        self.message_queue.append(message)
    
    async def analyze(self, data: Dict[str, Any]) -> AgentResult:
        raise NotImplementedError
    
    def _create_result(self, output: Dict, reasoning: str, 
                       confidence: float, exec_time: float, 
                       recommendations: List[str] = None) -> AgentResult:
        return AgentResult(
            agent_name=self.name,
            status=AgentStatus.COMPLETED,
            output=output,
            reasoning=reasoning,
            confidence=confidence,
            execution_time=exec_time,
            recommendations=recommendations or []
        )


class PredictionAgent(BaseAgent):
    """
    Agent 1: Prediction Agent
    Forecasts infection spread over time using SEIR model outputs and trend analysis
    """
    
    def __init__(self):
        super().__init__(
            name="Prediction Agent",
            description="Forecasts infection spread trajectories and key metrics over time"
        )
    
    async def analyze(self, data: Dict[str, Any]) -> AgentResult:
        start_time = time.time()
        self.status = AgentStatus.RUNNING
        
        try:
            simulation_result = data.get("simulation_result", {})
            timeline = simulation_result.get("timeline", [])
            region = data.get("region", {})
            
            if not timeline:
                raise ValueError("No simulation timeline provided")
            
            # Extract key metrics
            peak_infected = simulation_result.get("peak_infected", 0)
            peak_day = simulation_result.get("peak_day", 0)
            total_infected = simulation_result.get("total_infected", 0)
            r0 = simulation_result.get("r0", 1.0)
            population = region.get("population", 1000000)
            
            # Forecast analysis
            attack_rate = (total_infected / population) * 100 if population > 0 else 0
            days_to_peak = peak_day
            
            # Trend analysis from recent data
            recent_days = timeline[-14:] if len(timeline) >= 14 else timeline
            if len(recent_days) >= 2:
                trend = recent_days[-1]["infected"] - recent_days[0]["infected"]
                trend_direction = "increasing" if trend > 0 else ("decreasing" if trend < 0 else "stable")
            else:
                trend_direction = "insufficient_data"
            
            # Compute weekly projections
            weekly_projections = []
            weeks = [7, 14, 21, 28, 60, 90]
            for week_day in weeks:
                if week_day < len(timeline):
                    entry = timeline[week_day]
                    weekly_projections.append({
                        "day": week_day,
                        "week": week_day // 7,
                        "infected": entry["infected"],
                        "cumulative": entry["cumulative_cases"]
                    })
            
            # Healthcare capacity assessment
            hospital_capacity = region.get("hospital_capacity", population * 0.003)
            capacity_breach_day = None
            for entry in timeline:
                if entry["infected"] > hospital_capacity:
                    capacity_breach_day = entry["day"]
                    break
            
            output = {
                "r0": r0,
                "r_effective_current": round(r0 * (timeline[0]["susceptible"] / population), 2) if timeline else r0,
                "peak_infected": round(peak_infected),
                "peak_infected_pct": round((peak_infected / population) * 100, 2),
                "peak_day": peak_day,
                "total_infected": round(total_infected),
                "attack_rate_pct": round(attack_rate, 2),
                "trend_direction": trend_direction,
                "weekly_projections": weekly_projections,
                "hospital_capacity": round(hospital_capacity),
                "capacity_breach_day": capacity_breach_day,
                "epidemic_end_day": simulation_result.get("epidemic_end_day"),
                "severity_level": self._classify_severity(r0, attack_rate, peak_infected, population)
            }
            
            reasoning = (
                f"With R0={r0:.2f}, the epidemic is classified as "
                f"{'supercritical (explosive growth)' if r0 > 2 else 'critical' if r0 > 1.5 else 'moderate' if r0 > 1 else 'subcritical'}. "
                f"Peak infections of {round(peak_infected):,} are expected on day {peak_day}, "
                f"representing {round(attack_rate, 1)}% of the population. "
                f"{'Healthcare capacity will be exceeded on day ' + str(capacity_breach_day) if capacity_breach_day else 'Healthcare capacity appears sufficient'}."
            )
            
            recommendations = self._generate_recommendations(r0, attack_rate, capacity_breach_day, peak_day)
            
            self.status = AgentStatus.COMPLETED
            return self._create_result(output, reasoning, 
                                        min(0.95, 0.7 + (len(timeline) / 1000)),
                                        time.time() - start_time, recommendations)
        
        except Exception as e:
            self.status = AgentStatus.ERROR
            logger.error(f"PredictionAgent error: {e}")
            return AgentResult(
                agent_name=self.name, status=AgentStatus.ERROR,
                output={"error": str(e)}, reasoning="Analysis failed",
                confidence=0.0, execution_time=time.time() - start_time
            )
    
    def _classify_severity(self, r0: float, attack_rate: float, 
                           peak_infected: float, population: int) -> str:
        peak_pct = (peak_infected / population) * 100 if population > 0 else 0
        if r0 > 2.5 or peak_pct > 10:
            return "CRITICAL"
        elif r0 > 1.5 or peak_pct > 5:
            return "HIGH"
        elif r0 > 1.0 or peak_pct > 2:
            return "MODERATE"
        else:
            return "LOW"
    
    def _generate_recommendations(self, r0: float, attack_rate: float, 
                                   capacity_breach_day: Optional[int], 
                                   peak_day: int) -> List[str]:
        recs = []
        if r0 > 2:
            recs.append("Immediate intervention required - R0 exceeds critical threshold of 2.0")
        if capacity_breach_day and capacity_breach_day < 30:
            recs.append(f"Healthcare system will be overwhelmed in {capacity_breach_day} days - surge capacity needed")
        if peak_day < 21:
            recs.append("Rapid epidemic progression detected - accelerated response protocols required")
        if attack_rate > 20:
            recs.append("High population attack rate projected - population-wide measures recommended")
        if not recs:
            recs.append("Monitor situation closely with daily surveillance updates")
        return recs


class RiskAnalysisAgent(BaseAgent):
    """
    Agent 2: Risk Analysis Agent
    Identifies high-risk zones and ranks severity across the region
    """
    
    def __init__(self):
        super().__init__(
            name="Risk Analysis Agent",
            description="Identifies and ranks high-risk zones based on multiple risk factors"
        )
    
    async def analyze(self, data: Dict[str, Any]) -> AgentResult:
        start_time = time.time()
        self.status = AgentStatus.RUNNING
        
        try:
            region = data.get("region", {})
            simulation_result = data.get("simulation_result", {})
            weather_data = data.get("weather_data", {})
            prediction_output = data.get("prediction_output", {})
            
            zones = region.get("zones") or []
            if not zones:
                logger.warning("RiskAnalysisAgent: no zones in region data — using region as single zone")
                zones = [{
                    "id": "zone_1", "name": region.get("name", "Region"),
                    "population": region.get("population", 1000000),
                    "population_density": region.get("density", 5000),
                    "mobility_index": 0.75,
                    "hospital_beds_per_1000": region.get("hospital_beds_per_1000", 2.5),
                    "elderly_population_pct": region.get("elderly_population_pct", 12),
                    "current_cases": prediction_output.get("peak_infected", 0) // 10,
                    "lat": region.get("lat", 0),
                    "lon": region.get("lon", 0),
                }]
            
            # Score each zone
            scored_zones = []
            for zone in zones:
                risk_score = self._calculate_zone_risk(
                    zone, simulation_result, weather_data, prediction_output
                )
                scored_zones.append({
                    **zone,
                    "risk_score": risk_score["total"],
                    "risk_level": risk_score["level"],
                    "risk_factors": risk_score["factors"],
                    "priority_rank": 0  # Will be set after sorting
                })
            
            # Sort by risk score
            scored_zones.sort(key=lambda x: x["risk_score"], reverse=True)
            for i, zone in enumerate(scored_zones):
                zone["priority_rank"] = i + 1
            
            # Overall region risk
            avg_risk = sum(z["risk_score"] for z in scored_zones) / len(scored_zones) if scored_zones else 0
            high_risk_zones = [z for z in scored_zones if z["risk_level"] in ["HIGH", "CRITICAL"]]
            
            # Risk distribution
            risk_distribution = {
                "CRITICAL": len([z for z in scored_zones if z["risk_level"] == "CRITICAL"]),
                "HIGH": len([z for z in scored_zones if z["risk_level"] == "HIGH"]),
                "MODERATE": len([z for z in scored_zones if z["risk_level"] == "MODERATE"]),
                "LOW": len([z for z in scored_zones if z["risk_level"] == "LOW"])
            }
            
            # Environmental risk factors
            env_risk = self._assess_environmental_risk(weather_data)
            
            output = {
                "zones": scored_zones,
                "high_risk_zones": high_risk_zones,
                "high_risk_count": len(high_risk_zones),
                "average_risk_score": round(avg_risk, 2),
                "region_risk_level": self._score_to_level(avg_risk),
                "risk_distribution": risk_distribution,
                "environmental_risk": env_risk,
                "total_zones_analyzed": len(scored_zones),
                "alerts": self._generate_alerts(scored_zones, env_risk)
            }
            
            reasoning = (
                f"Analyzed {len(scored_zones)} zones. "
                f"{len(high_risk_zones)} zones classified as HIGH or CRITICAL risk. "
                f"Overall regional risk score: {round(avg_risk, 1)}/100. "
                f"Primary drivers: population density, mobility patterns, and healthcare capacity."
            )
            
            recommendations = [
                f"Prioritize interventions in {scored_zones[0]['name'] if scored_zones else 'top-ranked zone'} (Risk Score: {scored_zones[0]['risk_score']:.0f}/100)" if scored_zones else "No zones analyzed",
                f"Deploy additional testing resources to {len(high_risk_zones)} high-risk zones",
                "Implement targeted contact tracing in zones with risk score above 70",
                "Increase healthcare capacity in critical zones by at least 30%"
            ]
            
            # Confidence: computed from actual data richness and risk signal clarity
            # More zones + environmental data + prediction context = higher confidence
            zone_count_score   = min(1.0, len(scored_zones) / 8)          # 0..1
            risk_signal_score  = min(1.0, avg_risk / 80)                   # clearer risk → more confident
            weather_bonus      = 0.05 if bool(weather_data) else 0.0
            prediction_bonus   = 0.06 if bool(prediction_output) else 0.0
            confidence = round(
                0.65
                + 0.15 * zone_count_score
                + 0.09 * risk_signal_score
                + weather_bonus
                + prediction_bonus,
                3,
            )

            self.status = AgentStatus.COMPLETED
            return self._create_result(output, reasoning,
                                        confidence,
                                        time.time() - start_time, recommendations)
        
        except Exception as e:
            self.status = AgentStatus.ERROR
            logger.error(f"RiskAnalysisAgent error: {e}")
            return AgentResult(
                agent_name=self.name, status=AgentStatus.ERROR,
                output={"error": str(e)}, reasoning="Risk analysis failed",
                confidence=0.0, execution_time=time.time() - start_time
            )
    
    def _calculate_zone_risk(self, zone: Dict, simulation: Dict, 
                              weather: Dict, prediction: Dict) -> Dict:
        """Calculate composite risk score for a zone"""
        
        # Component scores (0-100)
        density_score = min(100, (zone.get("population_density", 5000) / 50000) * 100)
        
        mobility_score = zone.get("mobility_index", 0.7) * 100
        
        healthcare_score = 100 - min(100, (zone.get("hospital_beds_per_1000", 3) / 10) * 100)
        
        age_factor = zone.get("elderly_population_pct", 15)
        age_score = min(100, age_factor * 3)
        
        current_cases = zone.get("current_cases", 0)
        pop = zone.get("population", 100000)
        case_score = min(100, (current_cases / pop) * 10000) if pop > 0 else 0
        
        # Weighted composite
        weights = {
            "density": 0.25,
            "mobility": 0.20,
            "healthcare": 0.20,
            "age": 0.15,
            "cases": 0.20
        }
        
        total = (
            density_score * weights["density"] +
            mobility_score * weights["mobility"] +
            healthcare_score * weights["healthcare"] +
            age_score * weights["age"] +
            case_score * weights["cases"]
        )
        
        return {
            "total": round(total, 1),
            "level": self._score_to_level(total),
            "factors": {
                "population_density": round(density_score, 1),
                "mobility": round(mobility_score, 1),
                "healthcare_deficit": round(healthcare_score, 1),
                "vulnerable_population": round(age_score, 1),
                "current_burden": round(case_score, 1)
            }
        }
    
    def _score_to_level(self, score: float) -> str:
        if score >= 75: return "CRITICAL"
        elif score >= 55: return "HIGH"
        elif score >= 35: return "MODERATE"
        else: return "LOW"
    
    def _assess_environmental_risk(self, weather: Dict) -> Dict:
        temp = weather.get("temperature", 20)
        risk_boost = max(0, (15 - temp) / 15) * 20  # Cold weather boosts risk
        return {
            "temperature": temp,
            "risk_modifier": round(risk_boost, 1),
            "conditions": weather.get("conditions", "Unknown")
        }
    
    def _generate_alerts(self, zones: List[Dict], env_risk: Dict) -> List[Dict]:
        alerts = []
        for zone in zones[:3]:
            if zone["risk_level"] in ["CRITICAL", "HIGH"]:
                alerts.append({
                    "zone": zone["name"],
                    "level": zone["risk_level"],
                    "message": f"Elevated risk detected in {zone['name']} - immediate attention required",
                    "score": zone["risk_score"]
                })
        return alerts
    


class PolicyRecommendationAgent(BaseAgent):
    """
    Agent 3: Policy Recommendation Agent
    Recommends optimal interventions with cost-benefit analysis
    """
    
    def __init__(self):
        super().__init__(
            name="Policy Recommendation Agent",
            description="Recommends optimal policy interventions with reasoning and cost-benefit analysis"
        )
        
        self.policy_database = {
            "full_lockdown": {
                "name": "Full Lockdown",
                "effectiveness": 0.75,
                "economic_cost": 0.90,
                "social_cost": 0.85,
                "implementation_speed": 0.95,
                "duration_weeks": 4,
                "description": "Complete closure of non-essential services and movement restrictions"
            },
            "partial_lockdown": {
                "name": "Partial Lockdown",
                "effectiveness": 0.50,
                "economic_cost": 0.55,
                "social_cost": 0.50,
                "implementation_speed": 0.90,
                "duration_weeks": 6,
                "description": "Targeted restrictions on high-risk activities while maintaining essential services"
            },
            "vaccination_rollout": {
                "name": "Accelerated Vaccination",
                "effectiveness": 0.65,
                "economic_cost": 0.20,
                "social_cost": 0.10,
                "implementation_speed": 0.40,
                "duration_weeks": 12,
                "description": "Priority vaccination of high-risk groups and essential workers"
            },
            "travel_restriction": {
                "name": "Travel Restrictions",
                "effectiveness": 0.30,
                "economic_cost": 0.40,
                "social_cost": 0.30,
                "implementation_speed": 0.85,
                "duration_weeks": 8,
                "description": "Restrict inter-zone and international travel to contain spread"
            },
            "school_closure": {
                "name": "School Closures",
                "effectiveness": 0.25,
                "economic_cost": 0.25,
                "social_cost": 0.45,
                "implementation_speed": 0.95,
                "duration_weeks": 6,
                "description": "Close educational institutions to reduce transmission in younger populations"
            },
            "combined_strategy": {
                "name": "Combined Targeted Strategy",
                "effectiveness": 0.80,
                "economic_cost": 0.60,
                "social_cost": 0.55,
                "implementation_speed": 0.75,
                "duration_weeks": 8,
                "description": "Targeted lockdowns in high-risk zones combined with vaccination and surveillance"
            }
        }
    
    async def analyze(self, data: Dict[str, Any]) -> AgentResult:
        start_time = time.time()
        self.status = AgentStatus.RUNNING
        
        try:
            prediction_output = data.get("prediction_output", {})
            risk_output = data.get("risk_output", {})
            region = data.get("region", {})
            
            severity = prediction_output.get("severity_level", "MODERATE")
            r0 = prediction_output.get("r0", 1.5)
            capacity_breach_day = prediction_output.get("capacity_breach_day")
            high_risk_zones = risk_output.get("high_risk_count", 0)
            
            # Score and rank all policies
            ranked_policies = []
            for policy_id, policy in self.policy_database.items():
                score = self._score_policy(policy, severity, r0, capacity_breach_day, high_risk_zones)
                ranked_policies.append({
                    "id": policy_id,
                    **policy,
                    "composite_score": score,
                    "cost_benefit_ratio": round(policy["effectiveness"] / max(0.1, policy["economic_cost"]), 2),
                    "recommended": False
                })
            
            ranked_policies.sort(key=lambda x: x["composite_score"], reverse=True)
            
            # Mark top recommendation
            if ranked_policies:
                ranked_policies[0]["recommended"] = True
            
            top_policy = ranked_policies[0] if ranked_policies else None
            
            # Phase-based implementation plan
            implementation_plan = self._create_implementation_plan(
                top_policy, severity, region
            )
            
            # Cost-benefit analysis
            cost_benefit = self._cost_benefit_analysis(ranked_policies, region)
            
            output = {
                "primary_recommendation": top_policy,
                "ranked_policies": ranked_policies,
                "implementation_plan": implementation_plan,
                "cost_benefit_analysis": cost_benefit,
                "urgency_level": self._determine_urgency(severity, capacity_breach_day),
                "confidence_level": self._confidence_assessment(severity, r0)
            }
            
            reasoning = (
                f"Given the {severity} severity classification with R0={r0:.2f} and "
                f"{high_risk_zones} high-risk zones, the '{top_policy['name'] if top_policy else 'N/A'}' strategy "
                f"offers the optimal balance of effectiveness ({top_policy['effectiveness']*100:.0f}%) vs economic cost "
                f"({top_policy['economic_cost']*100:.0f}%). "
                f"{'Immediate action required - healthcare capacity at risk.' if capacity_breach_day and capacity_breach_day < 30 else 'Proactive measures recommended to prevent escalation.'}"
            )
            
            recommendations = [
                f"Implement {top_policy['name']} immediately" if top_policy else "Develop response strategy",
                "Establish real-time surveillance and reporting system",
                "Pre-position medical supplies in high-risk zones",
                "Communicate policies clearly to maintain public compliance"
            ]
            
            # Confidence: driven by severity certainty and number of policies evaluated
            severity_confidence = {"CRITICAL": 0.95, "HIGH": 0.90, "MODERATE": 0.85, "LOW": 0.78}
            base_conf = severity_confidence.get(severity, 0.85)
            policy_coverage = min(1.0, len(ranked_policies) / 6)
            confidence = round(base_conf * 0.85 + policy_coverage * 0.10
                               + (0.05 if high_risk_zones > 0 else 0.0), 3)

            self.status = AgentStatus.COMPLETED
            return self._create_result(output, reasoning, confidence,
                                        time.time() - start_time, recommendations)
        
        except Exception as e:
            self.status = AgentStatus.ERROR
            logger.error(f"PolicyRecommendationAgent error: {e}")
            return AgentResult(
                agent_name=self.name, status=AgentStatus.ERROR,
                output={"error": str(e)}, reasoning="Policy analysis failed",
                confidence=0.0, execution_time=time.time() - start_time
            )
    
    def _score_policy(self, policy: Dict, severity: str, r0: float, 
                      capacity_breach_day: Optional[int], high_risk_zones: int) -> float:
        
        severity_weights = {
            "CRITICAL": {"effectiveness": 0.60, "speed": 0.30, "economy": 0.10},
            "HIGH":     {"effectiveness": 0.50, "speed": 0.25, "economy": 0.25},
            "MODERATE": {"effectiveness": 0.40, "speed": 0.20, "economy": 0.40},
            "LOW":      {"effectiveness": 0.30, "speed": 0.10, "economy": 0.60}
        }
        
        w = severity_weights.get(severity, severity_weights["MODERATE"])
        economy_score = 1 - policy["economic_cost"]
        
        score = (
            policy["effectiveness"] * w["effectiveness"] +
            policy["implementation_speed"] * w["speed"] +
            economy_score * w["economy"]
        ) * 100
        
        # Bonus for targeted approaches when high-risk zones are identified
        if high_risk_zones > 3 and "targeted" in policy["name"].lower():
            score += 10
        
        return round(score, 1)
    
    def _determine_urgency(self, severity: str, capacity_breach_day: Optional[int]) -> str:
        if severity == "CRITICAL" or (capacity_breach_day and capacity_breach_day < 14):
            return "IMMEDIATE"
        elif severity == "HIGH" or (capacity_breach_day and capacity_breach_day < 30):
            return "URGENT"
        elif severity == "MODERATE":
            return "ELEVATED"
        else:
            return "STANDARD"
    
    def _confidence_assessment(self, severity: str, r0: float) -> Dict:
        base_confidence = 0.85
        return {
            "overall": base_confidence,
            "epidemiological": 0.90,
            "economic": 0.75,
            "social": 0.70,
            "note": "Based on SEIR model projections and historical policy effectiveness data"
        }
    
    def _create_implementation_plan(self, policy: Optional[Dict], 
                                    severity: str, region: Dict) -> List[Dict]:
        if not policy:
            return []
        
        phases = [
            {
                "phase": 1,
                "name": "Immediate Response (Days 1-3)",
                "actions": [
                    "Activate emergency response committee",
                    f"Deploy surveillance teams to high-risk zones",
                    "Issue public health advisories",
                    "Coordinate with healthcare facilities"
                ]
            },
            {
                "phase": 2,
                "name": f"Implementation (Days 4-{policy['duration_weeks']*7//2})",
                "actions": [
                    f"Roll out {policy['name']} measures",
                    "Establish contact tracing infrastructure",
                    "Deploy testing centers in high-density areas",
                    "Launch public communication campaign"
                ]
            },
            {
                "phase": 3,
                "name": f"Sustained Response (Weeks 2-{policy['duration_weeks']})",
                "actions": [
                    "Monitor compliance and effectiveness metrics",
                    "Adjust measures based on real-time data",
                    "Scale healthcare capacity as needed",
                    "Evaluate trigger points for escalation or de-escalation"
                ]
            },
            {
                "phase": 4,
                "name": "Exit Strategy",
                "actions": [
                    "Define clear exit criteria (R-effective < 1.0)",
                    "Gradual phased reopening protocol",
                    "Maintain surveillance for resurgence",
                    "Document learnings for future preparedness"
                ]
            }
        ]
        
        return phases
    
    def _cost_benefit_analysis(self, policies: List[Dict], region: Dict) -> Dict:
        population = region.get("population", 1000000)
        gdp_per_capita = region.get("gdp_per_capita", 2000)
        
        analyses = []
        for policy in policies[:3]:
            # Simplified cost-benefit
            lives_saved = round(population * 0.001 * policy["effectiveness"] * 100)
            economic_loss_pct = policy["economic_cost"] * 15  # % of regional GDP
            social_impact = policy["social_cost"] * 100
            
            analyses.append({
                "policy": policy["name"],
                "estimated_lives_saved": lives_saved,
                "economic_cost_pct_gdp": round(economic_loss_pct, 1),
                "social_disruption_score": round(social_impact, 1),
                "effectiveness_pct": round(policy["effectiveness"] * 100, 1),
                "cost_effectiveness_ratio": round(lives_saved / max(1, economic_loss_pct), 1)
            })
        
        return {"policy_comparisons": analyses, "currency": "USD", "timeframe": "12 weeks"}


class SimulationAgent(BaseAgent):
    """
    Agent 4: Simulation Agent
    Runs what-if scenario analysis with different intervention strategies
    """
    
    def __init__(self):
        super().__init__(
            name="Simulation Agent",
            description="Executes what-if scenario analysis and compares intervention outcomes"
        )
    
    async def analyze(self, data: Dict[str, Any]) -> AgentResult:
        start_time = time.time()
        self.status = AgentStatus.RUNNING
        
        try:
            from models.seir_model import SEIRModel, SEIRParameters
            
            region = data.get("region", {})
            scenario_results = data.get("scenario_results", {})
            base_result = data.get("simulation_result", {})
            
            # Compare scenarios if available
            comparisons = []
            if scenario_results:
                for scenario_name, result in scenario_results.items():
                    base_infected = base_result.get("total_infected", 1)
                    scenario_infected = result.get("total_infected", 1)
                    reduction = ((base_infected - scenario_infected) / max(1, base_infected)) * 100
                    
                    comparisons.append({
                        "scenario": scenario_name,
                        "total_infected": result.get("total_infected", 0),
                        "peak_infected": result.get("peak_infected", 0),
                        "peak_day": result.get("peak_day", 0),
                        "total_deceased": result.get("total_deceased", 0),
                        "reduction_vs_baseline": round(reduction, 1),
                        "lives_saved": round(
                            (base_result.get("total_deceased", 0) - result.get("total_deceased", 0))
                        )
                    })
                
                comparisons.sort(key=lambda x: x["total_infected"])
            
            # Identify optimal scenario
            best_scenario = comparisons[0] if comparisons else None
            
            # What-if insights
            what_if_insights = self._generate_what_if_insights(comparisons, base_result, region)
            
            output = {
                "baseline": {
                    "total_infected": base_result.get("total_infected", 0),
                    "peak_infected": base_result.get("peak_infected", 0),
                    "total_deceased": base_result.get("total_deceased", 0)
                },
                "scenario_comparisons": comparisons,
                "best_scenario": best_scenario,
                "what_if_insights": what_if_insights,
                "sensitivity_analysis": self._sensitivity_summary(comparisons)
            }
            
            reasoning = (
                f"Analyzed {len(comparisons)} intervention scenarios. "
                f"The most effective intervention reduces infections by "
                f"{best_scenario['reduction_vs_baseline']:.1f}% compared to baseline. "
                f"Early intervention is consistently shown to be the highest-impact lever."
            ) if best_scenario else "Insufficient scenario data for comparison."
            
            recommendations = [
                f"Adopt '{best_scenario['scenario']}' strategy for maximum impact" if best_scenario else "Run multiple scenarios",
                "Early implementation dramatically improves outcomes - act within 7 days",
                "Combine pharmaceutical and non-pharmaceutical interventions for synergistic effects",
                "Model should be updated weekly with real-world surveillance data"
            ]
            
            # Confidence: driven by how many scenarios were available for comparison
            n_scenarios = len(comparisons)
            confidence = round(min(0.95, 0.65 + n_scenarios * 0.06), 3)

            self.status = AgentStatus.COMPLETED
            return self._create_result(output, reasoning, confidence,
                                        time.time() - start_time, recommendations)
        
        except Exception as e:
            self.status = AgentStatus.ERROR
            logger.error(f"SimulationAgent error: {e}")
            return AgentResult(
                agent_name=self.name, status=AgentStatus.ERROR,
                output={"error": str(e)}, reasoning="Scenario analysis failed",
                confidence=0.0, execution_time=time.time() - start_time
            )
    
    def _generate_what_if_insights(self, comparisons: List[Dict], 
                                    baseline: Dict, region: Dict) -> List[Dict]:
        insights = []
        
        for comp in comparisons:
            if comp["reduction_vs_baseline"] > 0:
                insights.append({
                    "scenario": comp["scenario"],
                    "key_finding": f"Reduces total infections by {comp['reduction_vs_baseline']:.1f}%",
                    "lives_saved": comp["lives_saved"],
                    "peak_delay_days": max(0, comp["peak_day"] - baseline.get("peak_day", 0)),
                    "recommendation": "Implement immediately" if comp["reduction_vs_baseline"] > 50 else "Consider as part of strategy"
                })
        
        return insights
    
    def _sensitivity_summary(self, comparisons: List[Dict]) -> Dict:
        if not comparisons:
            return {}
        
        reductions = [c["reduction_vs_baseline"] for c in comparisons if c["reduction_vs_baseline"] > 0]
        
        return {
            "min_reduction": min(reductions) if reductions else 0,
            "max_reduction": max(reductions) if reductions else 0,
            "avg_reduction": round(sum(reductions) / len(reductions), 1) if reductions else 0,
            "high_impact_scenarios": len([r for r in reductions if r > 50])
        }


class AgentOrchestrator:
    """
    Orchestrates all agents, manages communication, and synthesizes results
    """
    
    def __init__(self):
        self.prediction_agent = PredictionAgent()
        self.risk_agent = RiskAnalysisAgent()
        self.policy_agent = PolicyRecommendationAgent()
        self.simulation_agent = SimulationAgent()
        
        self.agents = {
            "prediction": self.prediction_agent,
            "risk": self.risk_agent,
            "policy": self.policy_agent,
            "simulation": self.simulation_agent
        }
    
    async def run_full_analysis(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Full multi-agent analysis pipeline
        Agents share outputs for enriched, collaborative analysis
        """
        
        start_time = time.time()
        results = {}
        
        # Phase 1: Run prediction and risk agents in parallel
        prediction_result, risk_result = await asyncio.gather(
            self.prediction_agent.analyze(data),
            self.risk_agent.analyze(data)
        )
        
        results["prediction"] = prediction_result
        results["risk"] = risk_result
        
        # Phase 2: Policy agent receives prediction + risk outputs
        enriched_data = {
            **data,
            "prediction_output": prediction_result.output,
            "risk_output": risk_result.output
        }
        
        policy_result = await self.policy_agent.analyze(enriched_data)
        results["policy"] = policy_result
        
        # Phase 3: Simulation agent receives all previous outputs
        full_data = {
            **enriched_data,
            "policy_output": policy_result.output
        }
        
        simulation_result = await self.simulation_agent.analyze(full_data)
        results["simulation"] = simulation_result
        
        # Synthesize final report
        synthesis = self._synthesize_results(results, data)
        
        return {
            "agents": {
                name: {
                    "name": result.agent_name,
                    "status": result.status.value,
                    "output": result.output,
                    "reasoning": result.reasoning,
                    "confidence": result.confidence,
                    "recommendations": result.recommendations,
                    "execution_time": round(result.execution_time, 3)
                }
                for name, result in results.items()
            },
            "synthesis": synthesis,
            "total_execution_time": round(time.time() - start_time, 3)
        }
    
    def _synthesize_results(self, results: Dict[str, AgentResult], 
                             original_data: Dict) -> Dict[str, Any]:
        """Synthesize all agent outputs into actionable summary"""
        
        pred = results["prediction"].output if results["prediction"].status == AgentStatus.COMPLETED else {}
        risk = results["risk"].output if results["risk"].status == AgentStatus.COMPLETED else {}
        policy = results["policy"].output if results["policy"].status == AgentStatus.COMPLETED else {}
        sim = results["simulation"].output if results["simulation"].status == AgentStatus.COMPLETED else {}
        
        # Collect all recommendations
        all_recommendations = []
        for result in results.values():
            if result.status == AgentStatus.COMPLETED:
                all_recommendations.extend(result.recommendations)
        
        # Determine overall system recommendation
        primary_policy = policy.get("primary_recommendation", {})
        urgency = policy.get("urgency_level", "STANDARD")
        severity = pred.get("severity_level", "MODERATE")
        
        return {
            "overall_severity": severity,
            "urgency": urgency,
            "primary_recommendation": primary_policy.get("name", "Monitor Situation") if primary_policy else "Monitor Situation",
            "key_metrics": {
                "r0": pred.get("r0", 0),
                "peak_infected": pred.get("peak_infected", 0),
                "attack_rate_pct": pred.get("attack_rate_pct", 0),
                "high_risk_zones": risk.get("high_risk_count", 0),
                "total_zones": risk.get("total_zones_analyzed", 0)
            },
            "top_recommendations": all_recommendations[:6],
            "alerts": risk.get("alerts", []),
            "best_scenario": sim.get("best_scenario", {}),
            "confidence_summary": {
                "prediction": results["prediction"].confidence,
                "risk": results["risk"].confidence,
                "policy": results["policy"].confidence,
                "simulation": results["simulation"].confidence,
                "overall": round(
                    sum(r.confidence for r in results.values()) / len(results), 2
                )
            }
        }
