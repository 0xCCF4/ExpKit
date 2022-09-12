import re
from pathlib import Path
from typing import List, Optional, Dict

from expkit.base.architecture import TargetPlatform
from expkit.base.logger import get_logger
from expkit.base.payload import Payload, PayloadType
from expkit.base.stage.base import StageTemplate
from expkit.base.stage.context import StageContext
from expkit.base.task.base import TaskTemplate
from expkit.base.utils.files import recursive_foreach_file
from expkit.database.tasks.general.utils.tar_folder import TarTaskOutput
from expkit.framework.database import register_stage, TaskDatabase, auto_stage_group


LOGGER = get_logger(__name__)


@auto_stage_group("COMPILE_CSHARP", "Compiles C# source code to a binary.")
@register_stage
class CompileCSharpWindows(StageTemplate):
    def __init__(self):
        super().__init__(
            name="stages.compile.win.csharp",
            description="Compiles C# source code to a binary.",
            platform=TargetPlatform.WINDOWS,
            required_parameters={
                "BUILD_TYPE": Optional[str],  # Release or Debug
                "BUILD_ARGS": Optional[List[str]],
                "BUILD_ENV": Optional[Dict[str, str]],
                "BUILD_CONSTANTS": Optional[List[str]],
                "BUILD_PROJECT_FILENAME": Optional[str],
                "BUILD_MSBUILD_EXE": Optional[str],
            }
        )

        self.add_task("tasks.general.utils.untar_folder")
        self.add_task("tasks.compile.msbuild_project")
        self.add_task("tasks.general.utils.tar_folder")

        assert len(self.tasks) == 0 or len(self.tasks) == 3

    def execute_task(self, context: StageContext, index: int, task: TaskTemplate):
        task_parameters = {}

        if task.name == "tasks.general.utils.untar_folder":
            task_parameters["folder"] = context.build_directory
            task_parameters["tarfile"] = context.initial_payload.get_content()

            status = task.execute(task_parameters, context.build_directory, self)

            if not status.success:
                raise Exception("Failed to untar folder.")

        elif task.name == "tasks.compile.win.csharp":
            task_parameters["BUILD_TYPE"] = context.parameters.get("BUILD_TYPE", "Release")
            task_parameters["BUILD_ARGS"] = context.parameters.get("BUILD_ARGS", None)
            task_parameters["BUILD_ENV"] = context.parameters.get("BUILD_ENV", None)
            task_parameters["BUILD_CONSTANTS"] = context.parameters.get("BUILD_CONSTANTS", None)
            task_parameters["BUILD_MSBUILD_EXE"] = context.parameters.get("BUILD_MSBUILD_EXE", None)

            project_file_name = context.parameters.get("BUILD_PROJECT_FILENAME", None)

            project_file = None

            if project_file_name is None:
                found = False
                for file in context.build_directory.iterdir():
                    if file.exists() and file.is_file() and file.suffix == ".csproj":
                        project_file = file
                        if not found:
                            found = True
                        else:
                            LOGGER.error(f"Multiple project files found in {context.build_directory.absolute()}")
                            raise Exception("Multiple project files found.")
                if not found:
                    LOGGER.error(f"No project files found in {context.build_directory.absolute()}")
                    raise Exception("No project files found.")

            if project_file_name is not None:
                project_file = context.build_directory / project_file_name

                if not project_file.exists() or not project_file.is_file() or not project_file.suffix == ".csproj":
                    raise Exception("Specified project file does not exist or is not a valid .csproj file.")

            net_info = self._parse_csproj(project_file)
            if net_info["net_output"] is None or net_info["net_framework"] is None:
                raise Exception("Failed to parse .csproj file.")

            context.set("build_info", {**net_info, "net_type": task_parameters["BUILD_TYPE"]})

            task_parameters["BUILD_PROJECT_FILE"] = project_file

            status = task.execute(task_parameters, context.build_directory, self)

            if not status.success:
                raise Exception("Failed to compile C# project.")

        elif task.name == "tasks.general.utils.tar_folder":
            task_parameters["folder"] = context.build_directory

            status = task.execute(task_parameters, context.build_directory, self)

            if not status.success:
                raise Exception("Failed to tar folder.")

            assert isinstance(status, TarTaskOutput)

            context.set("output", status.data)

    def finish_build(self, context: StageContext) -> Payload:
        assert context.get("output") is not None

        meta = context.initial_payload.get_meta()
        meta = {**meta, **context.get("build_info")}

        return context.initial_payload.copy(
            type=PayloadType.CSHARP_PROJECT,
            content=context.get("output"),
            meta=meta
        )

    def _parse_csproj(self, csproj_file: Path) -> Dict[str, str]:
        content = csproj_file.read_text()

        def get_value(key: str) -> Optional[str]:
            match = re.search(f"<{key}> *([^<]*) *<\\/{key}>", content)
            if match is not None:
                return match.group(1)
            return None

        return {
            "net_output": get_value("OutputType"),
            "net_framework": get_value("TargetFramework"),
        }

    def get_supported_input_payload_types(self) -> List[PayloadType]:
        return [PayloadType.CSHARP_PROJECT]

    def get_output_payload_type(self, input: PayloadType, dependencies: List[PayloadType]) -> List[PayloadType]:
        return [PayloadType.DOTNET_BINARY] if input == PayloadType.CSHARP_PROJECT else []
