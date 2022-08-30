import copy
from pathlib import Path
from typing import Dict, Type, List

from expkit.base.payload import PayloadType, Payload
from expkit.base.architecture import PlatformArchitecture

from expkit.base.utils import type_checking, check_dict_types, error_on_fail


class StageTaskTemplate():
    """Perform an operation on within a virtual environment."""

    @type_checking
    def __init__(self, name: str, description: str, platform: PlatformArchitecture, parameters: Dict[str, any]):
        self.name = name
        self.description = description
        self.platform = platform
        self.parameters = parameters

    def execute(self, parameters: dict) -> bool:
        error_on_fail(check_dict_types(self.parameters, parameters), "StageTaskTemplate parameters")
        return True


class StageTemplate():
    """Performs a transformation on a payload by executing multiple tasks."""

    @type_checking
    def __init__(self, name: str, description: str, platform: PlatformArchitecture, input: PayloadType, output: PayloadType, template_directory: Path, parameters: Dict[str, Type]):
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

    @type_checking
    def execute(self, payload: Payload, parameters: dict, build_directory: Path) -> Payload:
        pass # TODO


class StageTemplateGroup():
    """Representation of a platform-independent stage template group."""

    @type_checking
    def __init__(self, name: str, description: str, tasks: Dict[PlatformArchitecture, StageTemplate]):
        self.name = name
        self.description = description
        self.tasks: Dict[PlatformArchitecture, StageTemplate] = tasks

    @type_checking
    def execute(self, payload: Payload, parameters: dict, build_directory: Path) -> Payload:
        task = self.tasks.get(payload.platform, None)

        if task is None:
            raise ValueError(f"StageTemplateGroup contains no tasks for the given platform {payload.platform}")

        return task.execute(payload, parameters, build_directory)

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.name

