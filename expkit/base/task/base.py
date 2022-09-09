import inspect
import threading
from pathlib import Path
from typing import Optional, Dict

from expkit.base.architecture import TargetPlatform
import expkit
from expkit.base.utils.type_checking import type_guard


class TaskOutput:
    def __init__(self, success: bool):
        self.success = success


class TaskTemplate():
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

    def execute(self, parameters: dict, build_directory: Path, stage: "expkit.base.stage.base.StageTemplate") -> TaskOutput:
        raise NotImplementedError("")


