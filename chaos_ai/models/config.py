import datetime
from enum import Enum
from typing import Dict, List, Optional, Union
from pydantic import BaseModel, Field, field_validator, model_validator
import chaos_ai.constants as const
from chaos_ai.models.cluster_components import ClusterComponents
from chaos_ai.utils import id_generator


class PodScenarioConfig(BaseModel):
    enable: bool = False


class AppOutageScenarioConfig(BaseModel):
    enable: bool = False


class ContainerScenarioConfig(BaseModel):
    enable: bool = False


class NodeHogScenarioConfig(BaseModel):
    enable: bool = False

class TimeScenarioConfig(BaseModel):
    enable: bool = False

class ScenarioConfig(BaseModel):
    application_outages: Optional[AppOutageScenarioConfig] = Field(
        alias="application-outages", default=None
    )
    pod_scenarios: Optional[PodScenarioConfig] = Field(
        alias="pod-scenarios", default=None
    )
    container_scenarios: Optional[ContainerScenarioConfig] = Field(
        alias="container-scenarios", default=None
    )
    node_cpu_hog: Optional[NodeHogScenarioConfig] = Field(
        alias="node-cpu-hog", default=None
    )
    node_memory_hog: Optional[NodeHogScenarioConfig] = Field(
        alias="node-memory-hog", default=None
    )
    time_scenarios: Optional[TimeScenarioConfig] = Field(
        alias="time-scenarios", default=None
    )


class FitnessFunctionType(str, Enum):
    point = 'point'
    range = 'range'


auto_id = id_generator()


class FitnessFunctionItem(BaseModel):
    id: int = Field(default_factory=lambda: next(auto_id))  # Auto-increment ID
    query: str  # PromQL
    type: FitnessFunctionType = FitnessFunctionType.point
    weight: float = 1.0

    @field_validator('weight', mode='after')
    @classmethod
    def is_percent(cls, value: float) -> float:
        if value < 0 or value > 1:
            raise ValueError(f'{value} is outside the range [0.0, 1.0]')
        return value


class FitnessFunction(BaseModel):
    query: Union[str, None] = None  # PromQL
    type: FitnessFunctionType = FitnessFunctionType.point
    include_krkn_failure: bool = True
    include_health_check_failure: bool = True
    include_health_check_response_time: bool = True
    items: List[FitnessFunctionItem] = []

    @model_validator(mode='after')
    def check_fitness_definition_exists(self):
        '''Validates whether there is at least one fitness function is defined.'''
        if self.query is None and len(self.items) == 0:
            raise ValueError("Please define at least one fitness function in query or items.")
        return self


class HealthCheckApplicationConfig(BaseModel):
    '''
    Health check configuration for the application.
    This is used to check the health of the application.
    '''
    name: str
    url: str
    status_code: int = 200  # Expected status code
    timeout: int = 4   # in seconds
    interval: int = 2   # in seconds

class HealthCheckConfig(BaseModel):
    stop_watcher_on_failure: bool = False
    applications: List[HealthCheckApplicationConfig] = []

class HealthCheckResult(BaseModel):
    name: str
    timestamp: str = Field(default_factory=lambda: datetime.datetime.now().isoformat())
    response_time: float  # in seconds
    status_code: int    # actual status code
    success: bool       # True if status code is as expected
    error: Optional[str] = None # Error message if the status code is not as expected


class ConfigFile(BaseModel):
    kubeconfig_file_path: str  # Path to kubeconfig
    parameters: Dict[str, str] = {}

    generations: int = 20  # Total number of generations to run.
    population_size: int = 10  # Initial population size

    mutation_rate: float = const.MUTATION_RATE  # How often mutation should occur for each scenario parameter (0.0-1.0)
    crossover_rate: float = const.CROSSOVER_RATE    # How often crossover should occur for each scenario parameter (0.0-1.0)
    composition_rate: float = const.CROSSOVER_COMPOSITION_RATE  # How often a crossover would lead to composition (0.0-1.0)

    population_injection_rate: float = const.POPULATION_INJECTION_RATE  # How often a random samples gets added to new population (0.0-1.0)
    population_injection_size: int = const.POPULATION_INJECTION_SIZE    # What's the size of random samples that gets added to new population

    fitness_function: FitnessFunction
    health_checks: HealthCheckConfig = HealthCheckConfig()

    scenario: ScenarioConfig = ScenarioConfig()

    cluster_components: ClusterComponents
