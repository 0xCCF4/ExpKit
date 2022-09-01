import os
import threading
from pathlib import Path
from typing import Dict, Optional, Type, TypeVar, Generic, List, Callable
from expkit.base.logger import get_logger
from expkit.base.stage import StageTaskTemplate, StageTemplate, StageTemplateGroup
from importlib import import_module

from expkit.base.utils.files import recursive_foreach_file

LOGGER = get_logger(__name__)

T = TypeVar("T")
class RegisterAnnotationHelper(Generic[T]):
    def __init__(self):
        self._registered: List[T] = []
        self._lock = threading.Lock()
        self.finished = False

    def finalize(self, func: Callable[[T], None]):
        with self._lock:
            if self.finished and len(self._registered) > 0:
                raise RuntimeError("RegisterAnnotationHelper is finalized")
            for task in self._registered:
                func(task)
            self.finished = True

    def register(self, obj: T):
        with self._lock:
            if self.finished:
                LOGGER.error(f"Unable to register {obj} as the database initialization is completed")
            else:
                self._registered.append(obj)

__helper_tasks: RegisterAnnotationHelper[StageTaskTemplate] = RegisterAnnotationHelper()
__helper_stages: RegisterAnnotationHelper[StageTemplate] = RegisterAnnotationHelper()
__helper_stage_groups: RegisterAnnotationHelper[StageTemplateGroup] = RegisterAnnotationHelper()


def register_task(task: Type[StageTaskTemplate], *nargs, **kwargs):
    __helper_tasks.register(task(*nargs, **kwargs))


def register_stage(stage: Type[StageTemplate], *nargs, **kwargs):
    __helper_stages.register(stage(*nargs, **kwargs))


def register_stage_group(stage_group: Type[StageTemplateGroup], *nargs, **kwargs):
    __helper_stage_groups.register(stage_group(*nargs, **kwargs))


def auto_discover_databases(directory: Path, module_prefix: str = "expkit."):
    LOGGER.debug(f"Discovering database entries in {directory}")

    files = []
    recursive_foreach_file(directory, lambda f: files.append(f), lambda d: d.name != "__pycache__" and not d.name.startswith("test"))

    if len(module_prefix.strip()) > 0 and not module_prefix.endswith("."):
        module_prefix += "."
    for file in files:
        if file.name.endswith(".py") and not file.name.startswith("test"):
            module_name = f"{module_prefix}{str(file.relative_to(directory)).replace(os.sep, '.')[:-3]}"
            try:
                import_module(module_name)  # Calls to register_* will be executed
            except ImportError as e:
                LOGGER.error(f" - error importing module {module_name}")
                LOGGER.error(e)
                continue

    __helper_tasks.finalize(TaskDatabase.get_instance().add_task)
    __helper_stages.finalize(StageDatabase.get_instance().add_stage)
    __helper_stage_groups.finalize(StageGroupDatabase.get_instance().add_group)


class TaskDatabase():
    def __init__(self):
        self.tasks: Dict[str, StageTaskTemplate] = {}
        LOGGER.debug("Created task database")

    def add_task(self, task: StageTaskTemplate):
        assert task.name == task.name.lower(), "Only lower case task names are allowed"
        if task.name in self.tasks:
            raise ValueError(f"Task with name {task.name} already exists in the database")
        LOGGER.debug(f" - registered task {task.name}")
        self.tasks[task.name.lower()] = task

    def get_task(self, name: str) -> Optional[StageTaskTemplate]:
        return self.tasks.get(name, None)

    def __len__(self):
        return len(self.tasks)

    __instance: 'TaskDatabase' = None
    @staticmethod
    def get_instance() -> 'TaskDatabase':
        if TaskDatabase.__instance is None:
            TaskDatabase.__instance = TaskDatabase()
        return TaskDatabase.__instance


class StageDatabase():
    def __init__(self):
        self.stages: Dict[str, StageTemplate] = {}
        LOGGER.debug("Created stage database")

    def add_stage(self, stage: StageTemplate):
        assert stage.name == stage.name.lower(), "Only lower case stage names are allowed"
        if stage.name in self.stages:
            raise ValueError(f"Stage with name {stage.name} already exists in the database")
        LOGGER.debug(f" - registered stage {stage.name}")
        self.stages[stage.name.lower()] = stage

    def get_stage(self, name: str) -> Optional[StageTemplate]:
        return self.stages.get(name, None)

    def __len__(self):
        return len(self.stages)

    __instance: 'StageDatabase' = None
    @staticmethod
    def get_instance() -> 'StageDatabase':
        if StageDatabase.__instance is None:
            StageDatabase.__instance = StageDatabase()
        return StageDatabase.__instance


class StageGroupDatabase():
    def __init__(self):
        self.groups: Dict[str, StageTemplateGroup] = {}
        LOGGER.debug("Created stage group database")

    def add_group(self, group: StageTemplateGroup):
        assert group.name == group.name.lower(), "Only lower case stage group names are allowed"
        if group.name in self.groups:
            raise ValueError(f"Stage group with name {group.name} already exists in the database")
        LOGGER.debug(f" - registered stage group {group.name}")
        self.groups[group.name.lower()] = group

    def get_group(self, name: str) -> Optional[StageTemplateGroup]:
        return self.groups.get(name, None)

    def __len__(self):
        return len(self.groups)

    __instance: 'StageGroupDatabase' = None
    @staticmethod
    def get_instance() -> 'StageGroupDatabase':
        if StageGroupDatabase.__instance is None:
            StageGroupDatabase.__instance = StageGroupDatabase()
        return StageGroupDatabase.__instance
