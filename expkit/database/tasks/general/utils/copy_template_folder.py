import re
import shutil
from pathlib import Path
from typing import Optional, List

from expkit.base.architecture import TargetPlatform
from expkit.base.logger import get_logger
from expkit.base.stage import StageTaskTemplate, StageTemplate, TaskOutput
from expkit.base.utils.base import error_on_fail
from expkit.base.utils.files import recursive_foreach_file
from expkit.base.utils.type_checking import check_dict_types
from expkit.database.tasks.general.utils.abstract_foreach_file_task import AbstractForeachFileTask
from expkit.framework.database import register_task

LOGGER = get_logger(__name__)


@register_task
class CopyTemplateFolderTask(AbstractForeachFileTask):
    def __init__(self):
        super().__init__(
            name="task.general.utils.copy_template_folder",
            description="Copies the stage template folder to the build directory.",
            platform=TargetPlatform.ALL,
            required_parameters={}
        )

    def _get_origin_folder(self, parameters: dict, stage: StageTemplate) -> Optional[Path]:
        return stage.get_template_directory()

    def _prepare_task(self, parameters: dict, build_directory: Path, stage: StageTemplate) -> TaskOutput:
        LOGGER.debug(f"Copying template folder {stage} to {build_directory}")
        return super()._prepare_task(parameters, build_directory, stage)

    def _process_file(self, file: Path, origin: Path, build_directory: Path, parameters: dict, stage: StageTemplate) -> TaskOutput:
        target_file = build_directory / file.relative_to(self._get_origin_folder(parameters, stage))

        LOGGER.debug(f"Copying file {file} to {target_file}")

        if not target_file.parent.exists():
            target_file.parent.mkdir(parents=True)

        try:
            shutil.copy(file, target_file)
        except Exception as e:
            LOGGER.error(f"Failed to copy file {file} to {target_file}", e)
            return TaskOutput(success=False)


