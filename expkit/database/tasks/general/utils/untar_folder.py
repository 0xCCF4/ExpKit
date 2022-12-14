import io
import re
import shutil
import tarfile
from pathlib import Path
from typing import Optional, List

from expkit.base.architecture import TargetPlatform
from expkit.base.logger import get_logger
from expkit.base.stage.base import StageTemplate
from expkit.base.task.base import TaskTemplate, TaskOutput
from expkit.base.utils.base import error_on_fail
from expkit.base.utils.type_checking import check_dict_types
from expkit.framework.database import register_task

LOGGER = get_logger(__name__)


@register_task
class UntarFolderTask(TaskTemplate):
    def __init__(self):
        super().__init__(
            name="tasks.general.utils.untar_folder",
            description="Extracts an in memory tar folder to the disk.",
            platform=TargetPlatform.ALL,
            required_parameters=[
                ("folder", Path, "The folder to extract the tar file to."),
                ("tarfile", bytes, "The in-memory-tar file to extract."),
            ]
        )

    def execute(self, parameters: dict, build_directory: Path, stage: StageTemplate) -> TaskOutput:
        error_on_fail(check_dict_types(parameters, self.required_parameters_types), "Invalid parameters for task:")

        LOGGER.debug(f"Untaring folder {parameters['folder']}")

        target_folder = parameters["folder"]
        if not target_folder.exists() or not target_folder.is_dir():
            LOGGER.error(f"Target folder {target_folder} does not exist or is not a directory")
            return TaskOutput(success=False)

        tarfile_raw = io.BytesIO(parameters["tarfile"])
        try:
            with tarfile.open(fileobj=tarfile_raw) as tar:
                tar.extractall(path=target_folder)
        except Exception as e:
            LOGGER.error(f"Failed to untar {tarfile_raw} to {target_folder}", e)
            return TaskOutput(success=False)

        return TaskOutput(success=True)
