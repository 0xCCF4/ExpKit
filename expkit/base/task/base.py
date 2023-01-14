import inspect
import threading
from pathlib import Path
from typing import Optional, Dict, Tuple, List

from expkit.base.architecture import TargetPlatform
import expkit
from expkit.base.utils.type_checking import type_guard


class TaskOutput:
    def __init__(self, success: bool):
        self.success = success


class TaskTemplate():
    """Perform an operation on within a virtual environment."""

    #@type_guard
    def __init__(self, name: str, description: str, platform: TargetPlatform, required_parameters: List[Tuple[str, any, str]]):
        self.name = name
        self.description = description
        self.platform = platform

        self.required_parameters_types: Dict[str, any] = {}
        self.required_parameters_description: Dict[str, str] = {}

        for pname, ptype, pdescription in required_parameters:
            assert pname not in self.required_parameters_types, f"Parameter {pname} already exists"
            self.required_parameters_types[pname] = ptype
            self.required_parameters_description[pname] = pdescription

        self._lock = threading.Lock()

        assert not self.__module__.startswith("expkit.") or self.__module__ == f"expkit.database.{self.name}", f"{self.__module__} must be named expkit.database.{self.name} or originiate from other package"
        assert self.name.startswith("tasks."), f"{self.name} must start with 'tasks.'"

    def get_required_parameters_info(self) -> Dict[str, Tuple[any, str]]:
        return {k: (v, self.required_parameters_description[k]) for k, v in self.required_parameters_types.items()}

    def get_template_directory(self) -> Optional[Path]:
        file = Path(inspect.getfile(self.__class__))
        file = file.parent / file.stem

        if file.exists() and file.is_dir():
            return file

        return None

    def execute(self, parameters: dict, build_directory: Path, stage: "expkit.base.stage.base.StageTemplate") -> TaskOutput:
        raise NotImplementedError("")


