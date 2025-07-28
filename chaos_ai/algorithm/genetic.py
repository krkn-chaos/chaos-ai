import os
import copy
import json
import yaml
import random
from typing import List

from chaos_ai.models.app import CommandRunResult, KrknRunnerType
from chaos_ai.models.base_scenario import (
    BaseScenario,
    Scenario,
    CompositeDependency,
    CompositeScenario,
    ScenarioFactory
)
from chaos_ai.models.config import ConfigFile
from chaos_ai.utils import id_generator
from chaos_ai.utils.logger import get_module_logger
from chaos_ai.chaos_engines.krkn_runner import KrknRunner

logger = get_module_logger(__name__)


class GeneticAlgorithm:
    '''
    A class implementing a Genetic Algorithm for scenario optimization.
    '''
    def __init__(self, 
        config: ConfigFile, 
        output_dir: str,
        runner_type: KrknRunnerType = None
    ):
        self.krkn_client = KrknRunner(
            config,
            output_dir=output_dir,
            runner_type=runner_type
        )
        self.output_dir = output_dir
        self.config = config
        self.population = []

        self.seen_population = {}  # Map between scenario and its result
        self.best_of_generation = []
        self.job_id_generator = id_generator()

        logger.info("CONFIG:")
        logger.info("%s", json.dumps(self.config.model_dump(), indent=2))

    def simulate(self):
        self.create_population(self.config.population_size)

        for i in range(self.config.generations):
            if len(self.population) == 0:
                logger.warning("No more population found, stopping generations.")
                break

            logger.info("| Population |")
            logger.info("--------------------------------------------------------")
            for scenario in self.population:
                logger.info("%s, ", scenario)
            logger.info("--------------------------------------------------------")

            logger.info("| Generation %d |", i + 1)
            logger.info("--------------------------------------------------------")

            # Evaluate fitness of the current population
            fitness_scores = [
                self.calculate_fitness(member, i) for member in self.population
            ]
            # Find the best individual in the current generation
            # Note: If there is no best solution, it will still consider based on sorting order
            fitness_scores = sorted(
                fitness_scores, key=lambda x: x.fitness_result.fitness_score, reverse=True
            )
            self.best_of_generation.append(fitness_scores[0])
            logger.info("Best Fitness: %f", fitness_scores[0].fitness_result.fitness_score)

            # We don't want to add a same parent back to population since its already been included
            for fitness_result in fitness_scores:
                self.seen_population[fitness_result.scenario] = fitness_result

            # Repopulate off-springs
            self.population = []
            for _ in range(self.config.population_size // 2):
                parent1, parent2 = self.select_parents(fitness_scores)
                child1, child2 = None, None
                if random.random() < self.config.composition_rate:
                    # componention crossover to generate 1 scenario
                    child1 = self.composition(
                        copy.deepcopy(parent1), copy.deepcopy(parent2)
                    )
                    child1 = self.mutate(child1)
                    self.population.append(child1)

                    child2 = self.composition(
                        copy.deepcopy(parent2), copy.deepcopy(parent1)
                    )
                    child2 = self.mutate(child2)
                    self.population.append(child2)
                else:
                    # Crossover of 2 parents to generate 2 offsprings
                    child1, child2 = self.crossover(
                        copy.deepcopy(parent1), copy.deepcopy(parent2)
                    )
                    child1 = self.mutate(child1)
                    child2 = self.mutate(child2)

                    self.population.append(child1)
                    self.population.append(child2)

            # Inject random members to population to diversify scenarios
            if random.random() < self.config.population_injection_rate:
                self.create_population(self.config.population_injection_size)

    def create_population(self, population_size):
        """Generate random population for algorithm"""
        logger.info("Creating random population")
        logger.info("Population Size: %d", self.config.population_size)

        already_seen = set()
        count = 0
        while count != population_size:
            scenario = ScenarioFactory.generate_random_scenario(self.config)
            # Mutate to generate initial randomness among same tests
            scenario = self.mutate(scenario)
            if scenario and scenario not in already_seen:
                self.population.append(scenario)
                already_seen.add(scenario)
                count += 1

    def calculate_fitness(self, scenario: BaseScenario, generation_id: int):
        # If scenario has already been run, do not run it again.
        # we will rely on mutation for the same parents to produce newer samples
        if scenario in self.seen_population:
            logger.info("Scenario %s already evaluated, skipping fitness calculation.", scenario)
            scenario = copy.deepcopy(self.seen_population[scenario])
            scenario.generation_id = generation_id
            return scenario
        scenario_result = self.krkn_client.run(scenario, generation_id)
        job_id = next(self.job_id_generator)
        self.save_scenario_result(job_id, scenario_result)
        return scenario_result

    def mutate(self, scenario: BaseScenario):
        if isinstance(scenario, CompositeScenario):
            scenario.scenario_a = self.mutate(scenario.scenario_a)
            scenario.scenario_b = self.mutate(scenario.scenario_b)
            return scenario
        for param in scenario.parameters:
            if random.random() < self.config.mutation_rate:
                param.mutate()
        return scenario

    def select_parents(self, fitness_scores: List[CommandRunResult]):
        """
        Selects two parents using Roulette Wheel Selection (proportionate selection).
        Higher fitness means higher chance of being selected.
        """
        total_fitness = sum([x.fitness_result.fitness_score for x in fitness_scores])

        scenarios = [x.scenario for x in fitness_scores]

        if total_fitness == 0:  # Handle case where all fitness scores are zero
            return random.choice(scenarios), random.choice(scenarios)

        # Normalize fitness scores to get probabilities
        probabilities = [x.fitness_result.fitness_score / total_fitness for x in fitness_scores]

        # Select parents based on probabilities
        parent1 = random.choices(scenarios, weights=probabilities, k=1)[0]
        parent2 = random.choices(scenarios, weights=probabilities, k=1)[0]
        return parent1, parent2

    def crossover(self, scenario_a: BaseScenario, scenario_b: BaseScenario):
        if isinstance(scenario_a, CompositeScenario) and isinstance(scenario_b, CompositeScenario):
            # Handle both scenario are composite
            # by swapping one of the branches
            scenario_a.scenario_b, scenario_b.scenario_b = scenario_b.scenario_b, scenario_a.scenario_b
            return scenario_a, scenario_b
        elif isinstance(scenario_a, CompositeScenario) or isinstance(scenario_b, CompositeScenario):
            # Only one of them is composite
            if isinstance(scenario_a, CompositeScenario):
                # Scenario A is composite and B is not
                # Swap scenario_a's right node with scenario_b
                a_b = scenario_a.scenario_b
                scenario_a.scenario_b = scenario_b
                return scenario_a, a_b
            else:
                # Scenario B is composite and A is not
                # Swap scenario_a's right node with scenario_b
                b_a = scenario_b.scenario_a
                scenario_b.scenario_a = scenario_a
                return b_a, scenario_b

        common_params = set([x.name for x in scenario_a.parameters]) & set(
            [x.name for x in scenario_b.parameters]
        )

        def find_param_index(scenario: Scenario, param_name):
            for i, param in enumerate(scenario.parameters):
                if param_name == param.name:
                    return i

        if len(common_params) == 0:
            # no common parameter, currenty we return parents as is and hope for mutation
            # adopt some different strategy
            return scenario_a, scenario_b
        else:
            # if there are common params, lets switch values between them
            for param in common_params:
                if random.random() < self.config.crossover_rate:
                    # find index of param in list
                    a_index = find_param_index(scenario_a, param)
                    b_index = find_param_index(scenario_b, param)

                    # swap param values
                    valueA = scenario_a.parameters[a_index].value
                    valueB = scenario_b.parameters[b_index].value

                    scenario_a.parameters[a_index].value = valueB
                    scenario_b.parameters[b_index].value = valueA

            return scenario_a, scenario_b

    def composition(self, scenario_a: BaseScenario, scenario_b: BaseScenario):
        # combines two scenario to create a single composite scenario
        dependency = random.choice([
            CompositeDependency.NONE,
            CompositeDependency.A_ON_B,
            CompositeDependency.B_ON_A
        ])
        composite_scenario = CompositeScenario(
            name="composite",
            scenario_a=scenario_a,
            scenario_b=scenario_b,
            dependency=dependency
        )
        return composite_scenario

    def save(self):
        '''Save run results'''
        # TODO: Create a single result file (results.json) that contains summary of all the results
        self.save_config()
        self.save_best_generations()

    def save_config(self):
        logger.info("Saving config file to config.yaml")
        output_dir = self.output_dir
        os.makedirs(output_dir, exist_ok=True)
        with open(
            os.path.join(output_dir, "config.yaml"),
            "w",
            encoding="utf-8"
        ) as f:
            config_data = self.config.model_dump(mode='json')
            yaml.dump(config_data, f, sort_keys=False)

    def save_best_generations(self):
        logger.info("Saving results to best_scenarios.json")
        output_dir = self.output_dir
        os.makedirs(output_dir, exist_ok=True)
        with open(
            os.path.join(output_dir, "best_scenarios.json"),
            "w",
            encoding="utf-8"
        ) as f:
            best_generations = self.best_of_generation[:]
            for i in range(len(best_generations)):
                scenario_result = best_generations[i].model_dump()
                del scenario_result['log']
                scenario_result['start_time'] = (scenario_result['start_time']).isoformat()
                scenario_result['end_time'] = (scenario_result['end_time']).isoformat()
                best_generations[i] = scenario_result
            json.dump(best_generations, f, indent=4)

    def save_log_file(self, job_id: str, log_data: str):
        dir_path = os.path.join(self.output_dir, 'logs')
        os.makedirs(dir_path, exist_ok=True)
        # Store log file in output directory under a "logs" folder.
        log_save_path = os.path.join(dir_path, "scenario_%s.log" % job_id)
        with open(log_save_path, 'w', encoding='utf-8') as f:
            f.write(log_data)
        return log_save_path

    def save_scenario_result(self, job_id: int, fitness_result: CommandRunResult):
        logger.debug("Saving scenario result for job %s", job_id)
        result = fitness_result.model_dump()
        generation_id = result['generation_id']
        result['job_id'] = job_id

        # Store log in a log file and update log location
        result['log'] = self.save_log_file(
            str(job_id),
            result['log']
        )
        # Convert timestamps to ISO string
        result['start_time'] = (result['start_time']).isoformat()
        result['end_time'] = (result['end_time']).isoformat()

        output_dir = os.path.join(self.output_dir, "json", "generation_%s" % generation_id)
        os.makedirs(output_dir, exist_ok=True)

        with open(
            os.path.join(output_dir, "scenario_%s.json" % job_id),
            "w",
            encoding="utf-8"
        ) as file_handler:
            json.dump(result, file_handler, indent=4)
