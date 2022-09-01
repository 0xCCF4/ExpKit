import re
import shutil
from pathlib import Path
from typing import Optional, List

from expkit.base.architecture import TargetPlatform
from expkit.base.logger import get_logger
from expkit.base.stage import StageTaskTemplate, StageTemplate
from expkit.base.utils.base import error_on_fail
from expkit.base.utils.files import recursive_foreach_file
from expkit.base.utils.type_checking import check_dict_types

LOGGER = get_logger(__name__)


class CopyTemplateFolder(StageTaskTemplate):
    def __init__(self):
        super().__init__(
            name="task.general.utils.copy_template_folder",
            description="Copies the stage template folder to the build directory.",
            platform=TargetPlatform.ALL,
            required_parameters={
                "exclude": Optional[List[str]], # list of files to exclude (regex format string)
                "include": Optional[List[str]]  # list of files to include (regex format string) - if not specified, all files are included
            }
        )

    def execute(self, parameters: dict, build_directory: Path, stage: StageTemplate) -> bool:
        LOGGER.debug(f"Copying template folder {stage} to {build_directory}")
        error_on_fail(check_dict_types(parameters, self.required_parameters), "Invalid parameters for task:")

        files = []
        template_directory = stage.get_template_directory()

        if template_directory is None:
            LOGGER.error(f"Template directory not found for stage {stage}")
            return False

        recursive_foreach_file(template_directory, lambda file: files.append(file), None, False)

        for file in files:
            rel_filename: str = str(file.relative_to(template_directory).as_posix())

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

            target_file = build_directory / file.relative_to(template_directory)

            LOGGER.debug(f"Copying file {rel_filename} to {target_file}")

            try:
                shutil.copy(file, target_file)
            except Exception as e:
                LOGGER.error(f"Failed to copy file {rel_filename} to {target_file}", e)
                return False

        return True

