import re
import shutil
from pathlib import Path
from typing import Optional

from expkit.base.architecture import TargetPlatform
from expkit.base.logger import get_logger
from expkit.base.stage.base import StageTemplate
from expkit.base.task.base import TaskOutput
from expkit.database.tasks.general.utils.abstract_foreach_file_task import AbstractForeachFileTask
from expkit.framework.database import register_task

LOGGER = get_logger(__name__)


@register_task
class CopyTemplateFolderTask(AbstractForeachFileTask):
    def __init__(self):
        super().__init__(
            name="tasks.general.utils.copy_template_folder",
            description="Copies the stage template folder to the build directory.",
            platform=TargetPlatform.ALL,
            required_parameters=[
                ("source", Path, "The source folder to copy from."),
                ("target", Path, "The target folder to copy to."),
            ]
        )

    def _get_origin_folder(self, parameters: dict, stage: StageTemplate) -> Optional[Path]:
        return parameters["source"]

    def _get_target_folder(self, parameters: dict, stage: StageTemplate) -> Optional[Path]:
        return parameters["target"]

    def _prepare_task(self, parameters: dict, build_directory: Path, stage: StageTemplate) -> TaskOutput:
        LOGGER.debug(f"Copying template folder {stage} to {build_directory}")
        return super()._prepare_task(parameters, build_directory, stage)

    def _process_file(self, file: Path, origin: Path, build_directory: Path, parameters: dict, stage: StageTemplate) -> TaskOutput:
        target_file = self._get_target_folder(parameters, stage) / file.relative_to(self._get_origin_folder(parameters, stage))

        LOGGER.debug(f"Copying file {file} to {target_file}")

        if not target_file.parent.exists():
            target_file.parent.mkdir(parents=True)

        try:
            shutil.copy(file, target_file)
        except Exception as e:
            LOGGER.error(f"Failed to copy file {file} to {target_file}", e)
            return TaskOutput(success=False)

        return TaskOutput(success=True)
