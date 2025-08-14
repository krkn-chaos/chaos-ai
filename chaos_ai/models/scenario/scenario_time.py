import random

from chaos_ai.models.scenario.base import Scenario
from chaos_ai.models.scenario.parameters import *


class TimeScenario(Scenario):
    name: str = "time-scenarios"
    object_type: ObjectTypeParameter = ObjectTypeParameter()
    label_selector: LabelSelectorParameter = LabelSelectorParameter()
    action_time: ActionTimeParameter = ActionTimeParameter()
    container_name: ContainerNameParameter = ContainerNameParameter()
    namespace: NamespaceParameter = NamespaceParameter()

    def __init__(self, **data):
        super().__init__(**data)
        self.mutate()

    @property
    def parameters(self):
        return [
            self.object_type,
            self.label_selector,
            self.action_time,
            self.container_name,
            self.namespace,
        ]

    def mutate(self):
        self.object_type.mutate()
        self.action_time.mutate()
        
        if self.object_type.value == "pod":
            namespace = random.choice(self._cluster_components.namespaces)
            all_labels = set()
            # select a random pod label
            for p in namespace.pods:
                for label, value in p.labels.items():
                    all_labels.add(f"{label}={value}")
            self.label_selector.value = random.choice(list(all_labels))
            self.namespace.value = namespace.name
        else:
            all_labels = set()
            # select a random node label
            for n in self._cluster_components.nodes:
                for label, value in n.labels.items():
                    all_labels.add(f"{label}={value}")
            self.label_selector.value = random.choice(list(all_labels))
            self.namespace.value = ""

