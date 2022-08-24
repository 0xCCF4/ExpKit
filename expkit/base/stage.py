from pathlib import Path
from typing import Dict, Type, List

from expkit.base.payload import PayloadType, Payload
from expkit.base.platform import Platform, PlatformDict

from expkit.base.utils import check_dict_types, error_on_fail, error_on_fail_any, FinishedDeserialization, check_type


class StageTaskTemplate(FinishedDeserialization):
    """Perform an operation on within a virtual environment."""

    def __init__(self, name: str, description: str, platform: Platform, parameters: Dict[str, Type]):
        self.name = name
        self.description = description
        self.platform = platform
        self.parameters = parameters

    def finish_deserialization(self):
        error_on_fail_any([
            check_type(str, self.name),
            check_type(str, self.description),
            check_type(Platform, self.platform),
            check_type(Dict[str, Type], self.parameters)
        ], "StageTaskTemplate deserialization")

    def execute(self, parameters: dict) -> bool:
        error_on_fail(check_dict_types(self.parameters, parameters), "StageTaskTemplate parameters")
        return True


class StageTemplate(FinishedDeserialization):
    """Performs a transformation on a payload by executing multiple tasks."""

    def __init__(self, name: str, description: str, platform: Platform, input: PayloadType, output: PayloadType, template_directory: Path, parameters: Dict[str, Type]):
        self.name = name
        self.description = description
        self.platform = platform
        self.input = input
        self.output = output
        self.template_directory = template_directory
        self.parameters = parameters

        self.tasks: List[StageTaskTemplate] = []

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.name

    def finish_deserialization(self):
        error_on_fail_any([
            check_type(str, self.name),
            check_type(str, self.description),
            check_type(Platform, self.platform),
            check_type(PayloadType, self.input),
            check_type(PayloadType, self.output),
            check_type(Path, self.template_directory),
            check_type(Dict[str, Type], self.parameters)
        ], "StageTemplate deserialization")

    def execute(self, payload: Payload, parameters: dict, build_directory: Path) -> Payload:
        error_on_fail(check_dict_types(self.parameters, parameters), "StageTemplate parameters")

        pass # TODO


class StageTemplateGroup(FinishedDeserialization):
    """Representation of a platform-independent stage template group."""

    def __init__(self, name: str, description: str, tasks: Dict[Platform, StageTemplate]):
        self.name = name
        self.description = description
        self.tasks: PlatformDict[StageTemplate] = PlatformDict()

        for k, v in tasks.items():
            self.tasks.add(k, v)

    def execute(self, payload: Payload, parameters: dict, build_directory: Path) -> Payload:
        task = self.tasks.get(payload.platform)

        if len(task) > 1:
            raise ValueError(f"StageTemplateGroup contains multiple tasks for the same platform {payload.platform}")
        elif len(task) == 0:
            raise ValueError(f"StageTemplateGroup contains no tasks for the given platform {payload.platform}")

        return task[0].execute(payload, parameters, build_directory)

    def finish_deserialization(self):
        for t in self.tasks:
            t.finish_deserialization()

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.name

