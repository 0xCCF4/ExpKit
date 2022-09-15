import base64
import re
from pathlib import Path
from typing import List, Optional, Callable, Dict, Tuple

from expkit.base.logger import get_logger
from expkit.base.architecture import TargetPlatform
from expkit.base.stage.base import StageTemplate
from expkit.base.task.base import TaskTemplate, TaskOutput
from expkit.base.utils.base import error_on_fail
from expkit.base.utils.type_checking import check_dict_types
from expkit.framework.database import register_task


LOGGER = get_logger(__name__)


class AbstractStringReplace(TaskTemplate):
    def __init__(self, name: str, description: str, platform: TargetPlatform, required_parameters: list):
        super().__init__(
            name=name,
            description=description,
            platform=platform,
            required_parameters=[
                ("files", List[Tuple[Path, Path]], "List of input and according output files."),
                *required_parameters,
            ]
        )

    def transform_source(self, source: str, parameters: dict) -> str:
        return source

    def execute(self, parameters: dict, build_directory: Path, stage: StageTemplate) -> TaskOutput:
        error_on_fail(check_dict_types(parameters, self.required_parameters_types), "Invalid parameters for task:")

        for target_path, origin_path in parameters["files"]:

            if not origin_path.exists() or not origin_path.is_file():
                LOGGER.error(f"Source file {origin_path} does not exist")
                return TaskOutput(success=False)

            if target_path.exists() and target_path.is_file():
                LOGGER.debug(f"Target source file {target_path} already exists")

            origin_source = origin_path.read_text("utf-8")

            LOGGER.debug(f"Transforming {origin_path} to {target_path} ({self.name})")
            target_source = self.transform_source(origin_source, parameters)

            target_path.write_text(target_source, "utf-8")
            return TaskOutput(success=True)
