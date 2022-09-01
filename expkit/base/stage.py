import copy
import inspect
from pathlib import Path
from typing import Dict, Type, List, Optional

from expkit.base.logger import get_logger
from expkit.base.payload import PayloadType, Payload
from expkit.base.architecture import TargetPlatform
from expkit.base.utils.type_checking import type_guard


LOGGER = get_logger(__name__)


class StageTaskTemplate():
    """Perform an operation on within a virtual environment."""

    @type_guard
    def __init__(self, name: str, description: str, platform: TargetPlatform, required_parameters: Dict[str, any]):
        self.name = name
        self.description = description
        self.platform = platform
        self.required_parameters = required_parameters

        assert not self.__module__.startswith("expkit.") or self.__module__ == f"expkit.database.{self.name}", f"{self.__module__} must be named expkit.database.{self.name} or originiate from other package"
        assert self.name.startswith("tasks."), f"{self.name} must start with 'tasks.'"

    def get_template_directory(self) -> Optional[Path]:
        file = Path(inspect.getfile(self.__class__))
        file = file.parent / file.stem

        if file.exists() and file.is_dir():
            return file

        return None

    def execute(self, parameters: dict, build_directory: Path, stage: "StageTemplate") -> bool:
        raise NotImplementedError("")


class StageTemplate():
    """Performs a transformation on a payload by executing multiple tasks."""

    @type_guard
    def __init__(self, name: str, description: str, platform: TargetPlatform, required_parameters: Dict[str, Type]):
        self.name = name
        self.description = description
        self.platform = platform
        self.required_parameters = required_parameters

        self.tasks: List[StageTaskTemplate] = []

        assert not self.__module__.startswith("expkit.") or self.__module__ == f"expkit.database.{self.name}", f"{self.__module__} must be named expkit.database.{self.name} or originiate from other package"
        assert self.name.startswith("stages."), f"{self.name} must start with 'tasks.'"

    def get_supporting_input_payload_types(self) -> List[PayloadType]:
        raise NotImplementedError("Not implemented")

    def get_output_payload_type(self, input: Optional[PayloadType]=None) -> Optional[PayloadType]:
        # output None if input is not supported
        raise NotImplementedError("Not implemented")

    def get_template_directory(self) -> Optional[Path]:
        file = Path(inspect.getfile(self.__class__))
        file = file.parent / file.stem

        if file.exists() and file.is_dir():
            return file

        return None

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.name

    def prepare_build_directory(self, payload: Payload, build_directory: Path) -> bool:
        raise NotImplementedError("Not implemented")

    def finish_build(self, payload: Payload, build_directory: Path) -> Payload:
        raise NotImplementedError("Not implemented")

    @type_guard
    def execute(self, payload: Payload, parameters: dict, build_directory: Path) -> Payload:
        LOGGER.debug(f"Executing stage {self.name} on payload {payload.type}")

        if payload.type not in self.get_supporting_input_payload_types():
            raise RuntimeError(f"Stage {self.name} does not support input payload type {payload.type}")

        self.prepare_build_directory(payload, build_directory)

        for task in self.tasks:
            task.execute(parameters, build_directory, self)

        return self.finish_build(payload, build_directory)


class StageTemplateGroup():
    """Representation of a platform-independent stage template group."""

    @type_guard
    def __init__(self, name: str, description: str, tasks: Dict[TargetPlatform, StageTemplate]):
        self.name = name
        self.description = description
        self.tasks: Dict[TargetPlatform, StageTemplate] = tasks

    @type_guard
    def execute(self, payload: Payload, parameters: dict, build_directory: Path) -> Payload:
        task = self.tasks.get(payload.platform, None)

        if task is None:
            raise ValueError(f"StageTemplateGroup contains no tasks for the given platform {payload.platform}")

        return task.execute(payload, parameters, build_directory)

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.name

