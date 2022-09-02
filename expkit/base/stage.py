import copy
import inspect
import os
import threading
from pathlib import Path
from typing import Dict, Type, List, Optional

from expkit.base.logger import get_logger
from expkit.base.payload import PayloadType, Payload
from expkit.base.architecture import TargetPlatform
from expkit.base.utils.type_checking import type_guard


LOGGER = get_logger(__name__)


class TaskOutput:
    def __init__(self, success: bool):
        self.success = success


class StageTaskTemplate():
    """Perform an operation on within a virtual environment."""

    @type_guard
    def __init__(self, name: str, description: str, platform: TargetPlatform, required_parameters: Dict[str, any]):
        self.name = name
        self.description = description
        self.platform = platform
        self.required_parameters = required_parameters

        self._lock = threading.Lock()

        assert not self.__module__.startswith("expkit.") or self.__module__ == f"expkit.database.{self.name}", f"{self.__module__} must be named expkit.database.{self.name} or originiate from other package"
        assert self.name.startswith("tasks."), f"{self.name} must start with 'tasks.'"

    def get_template_directory(self) -> Optional[Path]:
        file = Path(inspect.getfile(self.__class__))
        file = file.parent / file.stem

        if file.exists() and file.is_dir():
            return file

        return None

    def execute(self, parameters: dict, build_directory: Path, stage: "StageTemplate") -> TaskOutput:
        raise NotImplementedError("")


class StageContext:
    def __init__(self, initial_payload: Payload, parameters: dict, build_directory: Path):
        self.initial_payload = initial_payload
        self.parameters = parameters
        self.build_directory = build_directory
        self.data: Dict[str, any] = {}

    def get(self, key: str, default: any = None) -> any:
        return self.data.get(key, default)

    def set(self, key: str, value: any):
        self.data[key] = value

    def __delitem__(self, key):
        del self.data[key]

    def __getitem__(self, key):
        return self.data[key]

    def __setitem__(self, key, value):
        self.data[key] = value

    def __contains__(self, key):
        return key in self.data

    def __iter__(self):
        return iter(self.data)

    def __len__(self):
        return len(self.data)


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

    def get_supported_input_payload_types(self) -> List[PayloadType]:
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

    def prepare_build_directory(self, context: StageContext):
        if not context.build_directory.exists():
            LOGGER.info(f"Creating build directory {context.build_directory}")
            context.build_directory.mkdir(parents=True)
        if len(os.listdir(context.build_directory)) > 0:
            raise RuntimeError(f"Build directory {context.build_directory} is not empty..")

    def finish_build(self, context: StageContext) -> Payload:
        raise NotImplementedError("Not implemented")

    def execute_task(self, context: StageContext, index: int, task: StageTaskTemplate):
        raise NotImplementedError("Not implemented")

    @type_guard
    def execute(self, payload: Payload, parameters: dict, build_directory: Path) -> Payload:
        context: StageContext = StageContext(
            initial_payload=payload,
            parameters=parameters,
            build_directory=build_directory)

        LOGGER.debug(f"Executing stage {self.name} on payload {context.initial_payload.type}")

        if context.initial_payload.type not in self.get_supporting_input_payload_types():
            raise RuntimeError(f"Stage {self.name} does not support input payload type {context.initial_payload.type}")

        self.prepare_build_directory(context)

        for i, task in enumerate(self.tasks):
            self.execute_task(context, i, task)

        return self.finish_build(context)


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

