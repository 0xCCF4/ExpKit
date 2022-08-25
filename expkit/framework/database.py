import os
from pathlib import Path
from typing import Dict, Optional, Type
from expkit.base.logger import get_logger
from expkit.base.stage import StageTaskTemplate
from expkit.base.utils import recursive_foreach_file
from importlib import import_module

LOGGER = get_logger(__name__)


def discover_databases(directory: Path, module_prefix: str = "expkit."):
    LOGGER.debug(f"Discovering database entries in {directory}")

    files = []
    recursive_foreach_file(directory, lambda f: files.append(f), lambda d: d.name != "__pycache__")

    if len(module_prefix.strip()) > 0 and not module_prefix.endswith("."):
        module_prefix += "."
    for file in files:
        if file.name.endswith(".py"):
            module_name = f"{module_prefix}{str(file.relative_to(directory)).replace(os.sep, '.')[:-3]}"
            try:
                import_module(module_name)  # Calls to register_* will be executed
            except ImportError as e:
                LOGGER.error(f" - error importing module {module_name}")
                LOGGER.error(e)
                continue


def register_task(task: Type[StageTaskTemplate], *nargs, **kwargs):
    TaskDatabase.get_instance().add_task(task(*nargs, **kwargs))


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

    __instance: 'TaskDatabase' = None
    @staticmethod
    def get_instance() -> 'TaskDatabase':
        if TaskDatabase.__instance is None:
            TaskDatabase.__instance = TaskDatabase()
        return TaskDatabase.__instance


class StageDatabase():
    pass
