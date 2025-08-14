import random
from chaos_ai.models.scenario.base import BaseParameter

class DummyParameter(BaseParameter):
    name: str
    value: int


class NamespaceParameter(BaseParameter):
    name: str = "NAMESPACE"
    value: str = ""


class PodLabelParameter(BaseParameter):
    name: str = "POD_LABEL"
    value: str = ""  # Example: service=payment


class NamePatternParameter(BaseParameter):
    name: str = "NAME_PATTERN"
    value: str = ".*"


class DisruptionCountParameter(BaseParameter):
    name: str = "DISRUPTION_COUNT"
    value: int = 1


class KillTimeoutParameter(BaseParameter):
    name: str = "KILL_TIMEOUT"
    value: int = 60


class ExpRecoveryTimeParameter(BaseParameter):
    name: str = "EXPECTED_RECOVERY_TIME"
    value: int = 60



class DurationParameter(BaseParameter):
    name: str = "DURATION"
    value: int = 60



class PodSelectorParameter(BaseParameter):
    name: str = "POD_SELECTOR"
    value: str = "" # Format: {app: foo}


class BlockTrafficType(BaseParameter):
    name: str = "BLOCK_TRAFFIC_TYPE"
    value: str = "[Ingress, Egress]" # "[Ingress, Egress]", "[Ingress]", "[Egress]"


class LabelSelectorParameter(BaseParameter):
    name: str = "LABEL_SELECTOR"
    value: str = "" # Example Value: k8s-app=etcd


class ContainerNameParameter(BaseParameter):
    name: str = "CONTAINER_NAME"
    value: str = ""  # Example Value: etcd

class ActionParameter(BaseParameter):
    name: str = "ACTION"
    value: str = "1"
    # possible_values = ["1", "9"]


class TotalChaosDurationParameter(BaseParameter):
    name: str = "TOTAL_CHAOS_DURATION"
    value: int = 60
    krknctl_name: str = "chaos-duration"


class NodeCPUCoreParameter(BaseParameter):
    name: str = "NODE_CPU_CORE"
    value: float = 2
    krknctl_name: str = "cores"


class NodeCPUPercentageParameter(BaseParameter):
    '''
    CPU usage percentage of the node cpu hog scenario between 20 and 100.
    '''
    name: str = "NODE_CPU_PERCENTAGE"
    value: int = 50
    krknctl_name: str = "cpu-percentage"

    def mutate(self):
        if random.random() < 0.5:
            self.value += random.randint(1, 35) * self.value / 100
        else:
            self.value -= random.randint(1, 25) * self.value / 100
        self.value = int(self.value)
        self.value = max(self.value, 20)
        self.value = min(self.value, 100)

class NodeMemoryPercentageParameter(BaseParameter):
    '''
    Memory usage percentage of the node memory hog scenario between 20 and 100.
    '''
    name: str = "MEMORY_CONSUMPTION_PERCENTAGE"
    value: int = 50
    krknctl_name: str = "memory-consumption"

    def get_value(self):
        return f"{self.value}%"

    def mutate(self):
        if random.random() < 0.5:
            self.value += random.randint(1, 35) * self.value / 100
        else:
            self.value -= random.randint(1, 25) * self.value / 100
        self.value = int(self.value)
        self.value = max(self.value, 20)
        self.value = min(self.value, 100)


class NumberOfWorkersParameter(BaseParameter):
    name: str = "NUMBER_OF_WORKERS"
    value: int = 1
    krknctl_name: str = "memory-workers"

    def mutate(self):
        self.value = random.randint(1, 10)


class NodeSelectorParameter(BaseParameter):
    '''
    CPU-Hog:
    Node selector where the scenario containers will be scheduled in the format “=<selector>”. 
    NOTE: Will be instantiated a container per each node selected with the same scenario options. 
    If left empty a random node will be selected	

    Memory-Hog:
    defines the node selector for choosing target nodes. If not specified, one schedulable node in the cluster will be chosen at random. If multiple nodes match the selector, all of them will be subjected to stress. If number-of-nodes is specified, that many nodes will be randomly selected from those identified by the selector.	
    '''
    name: str = "NODE_SELECTOR"
    value: str = ""


class TaintParameter(BaseParameter):
    name: str = "TAINTS"
    value: str = '[]'


class NumberOfNodesParameter(BaseParameter):
    name: str = "NUMBER_OF_NODES"
    value: int = 1


class HogScenarioImageParameter(BaseParameter):
    name: str = "IMAGE"
    value: str = "quay.io/krkn-chaos/krkn-hog"

class ObjectTypeParameter(BaseParameter):
    name: str = "OBJECT_TYPE"
    value: str = ""  # Available Types: pod, node

    def mutate(self):
        self.value = random.choice(["pod", "node"])
 
class ActionTimeParameter(BaseParameter):
    name: str = "ACTION"
    value: str = "skew_date" # Available Types: skew_date, skew_time

    def mutate(self):
        self.value = random.choice(["skew_date", "skew_time"])
