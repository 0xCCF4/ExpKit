import re
from pathlib import Path
from typing import Optional, List

from expkit.base.architecture import TargetPlatform
from expkit.base.logger import get_logger
from expkit.base.stage.base import StageTemplate
from expkit.base.stage.context import StageContext
from expkit.base.task.base import TaskTemplate, TaskOutput
from expkit.base.utils.base import error_on_fail
from expkit.base.utils.files import recursive_foreach_file
from expkit.base.utils.type_checking import check_dict_types

LOGGER = get_logger(__name__)


class AbstractForeachFileTask(TaskTemplate):
    def __init__(self, name: str, description: str, platform: TargetPlatform, required_parameters: list):
        super().__init__(
            name=name,
            description=description,
            platform=platform,
            required_parameters=[
                ("exclude", Optional[List[str]], "List of files to exclude as list of regex match statement (default: exclude none)"),
                ("include", Optional[List[str]],  "List of files to include as list of regex match statements (default: include all files)"),
                *required_parameters,
            ]
        )

    def _get_origin_folder(self, parameters: dict, stage: StageTemplate) -> Optional[Path]:
        raise NotImplementedError("Abstract method")

    def _prepare_task(self, parameters: dict, build_directory: Path, stage: StageTemplate) -> TaskOutput:
        return TaskOutput(success=True)

    def _finalize_task(self, parameters: dict, build_directory: Path, stage: StageTemplate) -> TaskOutput:
        return TaskOutput(success=True)

    def _process_file(self, file: Path, origin: Path, build_directory: Path, parameters: dict, stage: StageTemplate) -> TaskOutput:
        raise NotImplementedError("Abstract method")

    def execute(self, parameters: dict, build_directory: Path, stage: StageTemplate) -> TaskOutput:
        error_on_fail(check_dict_types(parameters, self.required_parameters_types), "Invalid parameters for task:")

        status = self._prepare_task(parameters, build_directory, stage)
        if not status.success:
            return status

        files = []

        origin = self._get_origin_folder(parameters, stage)

        if origin is None or not origin.exists() or not origin.is_dir():
            LOGGER.error(f"Origin folder {origin} does not exist or is not a directory")
            return TaskOutput(success=False)

        recursive_foreach_file(origin, lambda file: files.append(file), None, False)

        for file in files:
            rel_filename: str = str(file.relative_to(origin).as_posix())

            if "exclude" in parameters:
                for exclude in parameters["exclude"]:
                    if re.match(exclude, rel_filename) is not None:
                        LOGGER.debug(f"Excluding file {rel_filename}")
                        continue
            if "include" in parameters:
                found_match = False
                for include in parameters["include"]:
                    if re.match(include, rel_filename) is None:
                        continue
                    found_match = True
                    break
                if not found_match:
                    LOGGER.debug(f"Not including file {rel_filename}")
                    continue

            status = self._process_file(file, origin, build_directory, parameters, stage)
            if not status.success:
                return status

        return self._finalize_task(parameters, build_directory, stage)

