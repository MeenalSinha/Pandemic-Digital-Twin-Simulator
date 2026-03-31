"""
SEIR Epidemiological Model
Susceptible -> Exposed -> Infected -> Recovered
Enhanced with intervention and environmental parameter adjustment
"""

import numpy as np
from scipy.integrate import odeint
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


@dataclass
class SEIRParameters:
    """
    Parameters for the SEIR model.

    NOTE ON ENVIRONMENTAL FACTORS:
    - density_factor and temperature_factor are stored for display/logging purposes only.
    - They are NOT multiplied again inside _seir_derivatives because data_service.py
      already bakes density_factor into beta during parameter derivation.
    - temperature_factor is applied once inside _seir_derivatives.
    - mobility_factor and intervention_factor are applied inside _seir_derivatives
      (set by apply_intervention() at scenario time, not by data_service).
    """
    beta: float = 0.3        # Transmission rate (already includes density adjustment)
    sigma: float = 0.2       # Incubation rate (1/incubation_period)
    gamma: float = 0.1       # Recovery rate (1/infectious_period)
    mu: float = 0.001        # Mortality rate
    population: int = 1000000
    initial_infected: int = 100
    initial_exposed: int = 200
    intervention_factor: float = 1.0  # Multiplier applied at scenario time
    vaccine_rate: float = 0.0         # Daily vaccination rate (fraction of susceptibles)

    # Environmental factors
    temperature_factor: float = 1.0  # Applied once in _seir_derivatives
    mobility_factor: float = 1.0     # Applied in _seir_derivatives (via intervention)
    # density_factor is stored for metadata only — already encoded in beta
    density_factor: float = 1.0


@dataclass
class SEIRState:
    """State of SEIR model at a given time"""
    time: float
    susceptible: float
    exposed: float
    infected: float
    recovered: float
    deceased: float
    vaccinated: float

    @property
    def total_population(self):
        # Include deceased: they were part of the population
        return self.susceptible + self.exposed + self.infected + self.recovered + self.deceased + self.vaccinated

    @property
    def active_cases(self):
        return self.infected

    @property
    def cumulative_cases(self):
        return self.infected + self.recovered + self.deceased

    @property
    def r_effective(self):
        """
        Effective reproduction number: R_eff = R0 * (S / N)
        Requires access to beta/gamma/mu which we don't store here;
        this is a simplified susceptible-fraction approximation.
        """
        denom = self.total_population
        if denom > 0:
            return self.susceptible / denom  # fraction susceptible; caller multiplies by R0
        return 0.0


@dataclass
class SimulationResult:
    """Complete simulation result"""
    parameters: SEIRParameters
    states: List[SEIRState]
    peak_infected: float
    peak_day: int
    total_infected: float
    total_deceased: float
    epidemic_end_day: Optional[int]
    r0: float          # Effective R0 (with intervention/environment multipliers)
    basic_r0: float = 0.0   # Baseline R0 (beta / (gamma + mu)), no multipliers
    scenario_name: str = "baseline"

    def to_dict(self) -> Dict:
        N = self.parameters.population or 1
        return {
            "scenario_name": self.scenario_name,
            "r0": round(self.r0, 2),
            "basic_r0": round(self.basic_r0, 2),
            "peak_infected": round(self.peak_infected),
            "peak_day": self.peak_day,
            "total_infected": round(self.total_infected),
            "total_deceased": round(self.total_deceased),
            "epidemic_end_day": self.epidemic_end_day,
            "timeline": [
                {
                    "day": int(s.time),
                    "susceptible": round(s.susceptible),
                    "exposed": round(s.exposed),
                    "infected": round(s.infected),
                    "recovered": round(s.recovered),
                    "deceased": round(s.deceased),
                    "vaccinated": round(s.vaccinated),
                    "active_cases": round(s.active_cases),
                    "cumulative_cases": round(s.cumulative_cases),
                    # True R_eff = R0 * susceptible_fraction
                    "r_effective": round(self.r0 * s.r_effective, 3),
                }
                for s in self.states
            ],
        }


class SEIRModel:
    """
    Enhanced SEIR Epidemiological Model
    Supports dynamic parameter adjustment and intervention modeling
    """
    
    def __init__(self, params: SEIRParameters):
        self.params = params
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def _seir_derivatives(self, y: List[float], t: float,
                           beta: float, sigma: float, gamma: float,
                           mu: float, N: int, vaccine_rate: float) -> List[float]:
        """
        SEIR differential equations.

        Effective beta applies:
          - intervention_factor  (set by apply_intervention; reflects NPI strength)
          - mobility_factor      (set by apply_intervention; reflects movement reduction)
          - temperature_factor   (environmental; set from weather data)
        density_factor is intentionally EXCLUDED here because data_service.py already
        multiplied it into beta when deriving parameters from regional data.

        Force-of-infection uses the live susceptible population (S+E+I+R+V) as the
        denominator so that vaccination-driven depletion of S is correctly accounted for.
        Deceased (D) are excluded from the mixing pool.
        """
        S, E, I, R, D, V = y

        # Active mixing population (excludes deceased)
        N_active = max(S + E + I + R + V, 1.0)

        effective_beta = (
            beta
            * self.params.intervention_factor
            * self.params.mobility_factor
            * self.params.temperature_factor
            # density_factor already encoded in beta — do NOT multiply again
        )

        # Force of infection
        lambda_ = effective_beta * I / N_active

        dS = -lambda_ * S - vaccine_rate * S
        dE =  lambda_ * S - sigma * E
        dI =  sigma * E - (gamma + mu) * I
        dR =  gamma * I
        dD =  mu * I
        dV =  vaccine_rate * S

        return [dS, dE, dI, dR, dD, dV]
    
    def run(self, days: int = 180, step: float = 1.0) -> SimulationResult:
        """Run the SEIR simulation for the configured number of days."""
        N = self.params.population
        I0 = min(self.params.initial_infected, N - 1)
        E0 = min(self.params.initial_exposed, N - I0 - 1)
        R0_init = 0
        D0 = 0
        V0 = 0
        S0 = N - I0 - E0  # Conserves total population at t=0

        y0 = [S0, E0, I0, R0_init, D0, V0]
        t = np.arange(0, days + step, step)

        solution = odeint(
            self._seir_derivatives, y0, t,
            args=(
                self.params.beta,
                self.params.sigma,
                self.params.gamma,
                self.params.mu,
                N,
                self.params.vaccine_rate,
            ),
            rtol=1e-6, atol=1e-8,
        )

        states = []
        for i, time_point in enumerate(t):
            S, E, I, R, D, V = solution[i]
            states.append(SEIRState(
                time=time_point,
                susceptible=max(0.0, S),
                exposed=max(0.0, E),
                infected=max(0.0, I),
                recovered=max(0.0, R),
                deceased=max(0.0, D),
                vaccinated=max(0.0, V),
            ))

        infected_values = [s.infected for s in states]
        peak_infected = max(infected_values)
        peak_day = int(np.argmax(infected_values))

        total_infected = states[-1].recovered + states[-1].infected + states[-1].deceased
        total_deceased = states[-1].deceased

        # Epidemic end: infections fall below 1 % of peak (after the peak)
        epidemic_end_day = None
        threshold = peak_infected * 0.01
        for i, s in enumerate(states[peak_day:], start=peak_day):
            if s.infected < threshold and i > peak_day + 10:
                epidemic_end_day = i
                break

        # Basic R0 (without interventions / environment) for reference
        basic_r0 = self.params.beta / (self.params.gamma + self.params.mu)

        # Effective (scenario) R0 — accounts for all applied multipliers
        effective_r0 = round(
            basic_r0
            * self.params.intervention_factor
            * self.params.mobility_factor
            * self.params.temperature_factor,
            2,
        )

        return SimulationResult(
            parameters=self.params,
            states=states,
            peak_infected=peak_infected,
            peak_day=peak_day,
            total_infected=total_infected,
            total_deceased=total_deceased,
            epidemic_end_day=epidemic_end_day,
            r0=effective_r0,
            basic_r0=basic_r0,
        )
    
    VALID_INTERVENTIONS = {
        "no_action",
        "partial_lockdown",
        "full_lockdown",
        "vaccination_rollout",
        "combined_strategy",
        "school_closure",
        "travel_restriction",
    }

    @staticmethod
    def apply_intervention(params: SEIRParameters, intervention_type: str) -> SEIRParameters:
        """
        Apply intervention effects to parameters.
        Raises ValueError for unknown intervention types instead of silently
        falling back to baseline, which would produce misleading output.
        """
        import copy

        if intervention_type not in SEIRModel.VALID_INTERVENTIONS:
            raise ValueError(
                f"Unknown intervention '{intervention_type}'. "
                f"Valid options: {sorted(SEIRModel.VALID_INTERVENTIONS)}"
            )

        new_params = copy.deepcopy(params)

        interventions = {
            "no_action": {
                "intervention_factor": 1.0,
                "vaccine_rate": 0.0,
                "mobility_factor": 1.0,
            },
            "partial_lockdown": {
                "intervention_factor": 0.6,
                "vaccine_rate": 0.001,
                "mobility_factor": 0.7,
            },
            "full_lockdown": {
                "intervention_factor": 0.25,
                "vaccine_rate": 0.001,
                "mobility_factor": 0.3,
            },
            "vaccination_rollout": {
                "intervention_factor": 0.85,
                "vaccine_rate": 0.005,
                "mobility_factor": 0.9,
            },
            "combined_strategy": {
                "intervention_factor": 0.35,
                "vaccine_rate": 0.004,
                "mobility_factor": 0.5,
            },
            "school_closure": {
                "intervention_factor": 0.75,
                "vaccine_rate": 0.0,
                "mobility_factor": 0.8,
            },
            "travel_restriction": {
                "intervention_factor": 0.7,
                "vaccine_rate": 0.0,
                "mobility_factor": 0.6,
            },
        }

        cfg = interventions[intervention_type]
        new_params.intervention_factor = cfg["intervention_factor"]
        new_params.vaccine_rate = cfg["vaccine_rate"]
        new_params.mobility_factor = cfg["mobility_factor"]

        return new_params
    
    @staticmethod
    def calculate_environmental_factors(weather_data: Dict) -> Dict[str, float]:
        """Calculate environmental transmission factors"""
        temp = weather_data.get("temperature", 20)
        humidity = weather_data.get("humidity", 60)
        
        # Temperature effect: lower temps increase respiratory virus spread
        if temp < 10:
            temp_factor = 1.2
        elif temp < 20:
            temp_factor = 1.05
        elif temp < 30:
            temp_factor = 0.95
        else:
            temp_factor = 0.85
        
        # Humidity effect
        if humidity < 30:
            humidity_factor = 1.1
        elif humidity < 60:
            humidity_factor = 1.0
        else:
            humidity_factor = 0.9
        
        return {
            "temperature_factor": temp_factor,
            "humidity_factor": humidity_factor,
            "combined_factor": temp_factor * humidity_factor
        }
