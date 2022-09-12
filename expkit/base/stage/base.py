import importlib
import inspect
import os
from pathlib import Path
from typing import List, Optional, Dict, Type, Union

from expkit.base.architecture import TargetPlatform
from expkit.base.logger import get_logger
from expkit.base.payload import PayloadType, Payload
from expkit.base.stage.context import StageContext
from expkit.base.task.base import TaskTemplate
from expkit.base.utils.type_checking import type_guard

LOGGER = get_logger(__name__)
_task_database = None


class StageTemplate():
    """Performs a transformation on a payload by executing multiple tasks."""

    @type_guard
    def __init__(self, name: str, description: str, platform: TargetPlatform, required_parameters: Dict[str, any]):
        self.name = name
        self.description = description
        self.platform = platform
        self.required_parameters = required_parameters

        self.tasks: List[TaskTemplate] = []

        assert not self.__module__.startswith("expkit.") or self.__module__ == f"expkit.database.{self.name}", f"{self.__module__} must be named expkit.database.{self.name} or originiate from other package"
        assert self.name.startswith("stages."), f"{self.name} must start with 'tasks.'"

    @type_guard
    def add_task(self, task: Union[TaskTemplate, str]):
        global _task_database
        if isinstance(task, str):
            if _task_database is None:
                # Break circular import
                _task_database = getattr(importlib.import_module("expkit.framework.database"), "TaskDatabase", None)

            assert _task_database is not None
            task = _task_database.get_instance().get_task(task)

        if task is None:
            return

        assert self.platform in self._get_task_platform_intersection(), f"Stage {self.name} target platform is not compatible with task {task.name}. Difference {self.platform.difference(self._get_task_platform_intersection())}"
        self.tasks.append(task)

    def get_supported_input_payload_types(self) -> List[PayloadType]:
        raise NotImplementedError("Not implemented")

    def get_output_payload_type(self, input: PayloadType, dependencies: List[PayloadType]) -> List[PayloadType]:
        raise NotImplementedError("Not implemented")

    def get_supported_dependency_types(self) -> List[List[PayloadType]]:
        return [[]]

    def _get_task_platform_intersection(self) -> TargetPlatform:
        platform = TargetPlatform.ALL
        for task in self.tasks:
            platform = platform.intersection(task.platform)

        return platform

    def is_supporting_dependencies(self, context: StageContext) -> bool:
        supported_all = self.get_supported_dependency_types()
        dependencies = context.dependencies

        for supported_entry in supported_all:
            if len(supported_entry) != len(dependencies):
                continue

            ok = True
            for a, b in zip(supported_entry, dependencies):
                if a != b.type:
                    ok = False
                    break

            if ok:
                return True

        return False

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

    def prepare_build(self, context: StageContext):
        if not context.build_directory.exists():
            LOGGER.info(f"Creating build directory {context.build_directory}")
            context.build_directory.mkdir(parents=True)
        if len(os.listdir(context.build_directory)) > 0:
            raise RuntimeError(f"Build directory {context.build_directory} is not empty..")

    def finish_build(self, context: StageContext) -> Payload:
        raise NotImplementedError("Not implemented")

    def execute_task(self, context: StageContext, index: int, task: TaskTemplate):
        raise NotImplementedError("Not implemented")

    @type_guard
    def execute(self, payload: Payload, output_type: PayloadType, dependencies: List[Payload], parameters: dict, build_directory: Path) -> Payload:
        context: StageContext = StageContext(
            initial_payload=payload,
            output_type=output_type,
            dependencies=dependencies,
            parameters=parameters,
            build_directory=build_directory)

        LOGGER.debug(f"Executing stage {self.name} on payload {context.initial_payload.type}")

        if context.initial_payload.type not in self.get_supported_input_payload_types():
            raise RuntimeError(f"Stage {self.name} does not support input payload type {context.initial_payload.type}")
        if not self.is_supporting_dependencies(context):
            raise RuntimeError(f"Stage {self.name} does not support dependencies types {context.dependencies}")
        if context.output_type not in self.get_output_payload_type(context.initial_payload.type, [d.type for d in context.dependencies]):
            raise RuntimeError(f"Stage {self.name} does not support output payload type {context.output_type}")

        self.prepare_build(context)

        for i, task in enumerate(self.tasks):
            self.execute_task(context, i, task)

        out_payload = self.finish_build(context)

        if out_payload.type != context.output_type:
            raise RuntimeError(f"Stage {self.name} produced payload of type {out_payload.type} instead of {context.output_type}")

        return out_payload
