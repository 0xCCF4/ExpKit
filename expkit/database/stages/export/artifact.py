import os
import shutil
from functools import wraps
from pathlib import Path
from typing import List, Optional

from expkit.base.architecture import TargetPlatform
from expkit.base.logger import get_logger
from expkit.base.payload import Payload, PayloadType
from expkit.base.stage.base import StageTemplate
from expkit.base.stage.context import StageContext
from expkit.base.task.base import TaskTemplate
from expkit.database.tasks.general.utils.tar_folder import TarTaskOutput
from expkit.framework.database import register_stage, TaskDatabase, auto_stage_group


LOGGER = get_logger(__name__)


@auto_stage_group("EXPORT", "Exports an artifact to the file system.")
@register_stage
class LoadProject(StageTemplate):
    def __init__(self):
        super().__init__(
            name="stages.export.artifact",
            description="Exports an artifact to the file system.",
            platform=TargetPlatform.ALL,
            required_parameters={
                "EXPORT_FOLDER_PATH": Optional[str], # The path to the folder where the artifact should be exported to (default cwd)
                "EXPORT_NAME": str,  # The name of the subfolder or file where the artifact should be exported to
            }
        )

        self.add_task("tasks.general.utils.untar_folder")

        assert len(self.tasks) == 0 or len(self.tasks) == 1

    def execute_task(self, context: StageContext, index: int, task: TaskTemplate):
        task_parameters = {}

        project = context.initial_payload.type.is_project()
        file = context.initial_payload.type.is_file()

        export_name = context.parameters.get("EXPORT_NAME")
        export_folder_path = context.parameters.get("EXPORT_FOLDER_PATH", None)

        if export_folder_path is None:
            export_folder_path = os.getcwd()
        export_folder_path = Path(export_folder_path)

        if not export_folder_path.exists() or not export_folder_path.is_dir():
            raise ValueError(f"Export root folder '{export_folder_path}' does not exist.")

        if project:
            if (export_folder_path / export_name).exists():
                shutil.rmtree(export_folder_path / export_name)
            (export_folder_path / export_name).mkdir(parents=True)

        if task.name == "tasks.general.utils.untar_folder":
            if project:
                task_parameters["folder"] = context.build_directory
                task_parameters["tarfile"] = context.initial_payload.get_content()

                status = task.execute(task_parameters, context.build_directory, self)

                if not status.success:
                    raise Exception("Failed to untar folder.")

                (context.build_directory / "info.json").write_text(context.initial_payload.get_json_metadata())
                shutil.copytree(context.build_directory, export_folder_path / export_name)

            if file:
                target_file = export_folder_path / export_name
                target_file.write_bytes(context.initial_payload.get_content())

                target_file = target_file.with_suffix(".json")
                target_file.write_text(context.initial_payload.get_json_metadata())

    def finish_build(self, context: StageContext) -> Payload:
        return context.initial_payload.copy()

    def get_supported_input_payload_types(self) -> List[PayloadType]:
        return PayloadType.get_all_types(include_empty=True)

    def get_output_payload_type(self, input: PayloadType, dependencies: List[PayloadType]) -> List[PayloadType]:
        return [input]

