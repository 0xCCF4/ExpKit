import os
import subprocess
import sys
from pathlib import Path
from typing import List, Optional, Dict

from expkit.base.logger import get_logger
from expkit.base.architecture import TargetPlatform, Platform
from expkit.base.stage.base import StageTemplate
from expkit.base.task.base import TaskTemplate, TaskOutput
from expkit.base.utils.base import error_on_fail
from expkit.base.utils.type_checking import check_dict_types
from expkit.framework.database import register_task


LOGGER = get_logger(__name__)


@register_task
class BuildMSBuildProject(TaskTemplate):
    def __init__(self):
        super().__init__(
            name="tasks.compile.msbuild_project",
            description="Compiles a msbuild project",
            platform=TargetPlatform.WINDOWS,
            required_parameters=[
                ("msbuild_path", Optional[Path], "Path to the msbuild executable (default: auto-detect)"),
                ("project_file", Optional[Path], "Path to the project file (default: auto-detect)"),
                ("build_type", str, "Build type (Release, Debug, etc.)"),
                ("additional_args", Optional[List[str]], "Additional arguments to pass to msbuild (default: none)"),
                ("additional_env", Optional[Dict[str, str]], "Additional environment variables to pass to msbuild (default: none)"),
                ("build_constants", Optional[List[str]], "Build constants to pass to msbuild (default: none)"),
            ]
        )

    def execute(self, parameters: dict, build_directory: Path, stage: StageTemplate) -> TaskOutput:
        error_on_fail(check_dict_types(parameters, self.required_parameters_types), "Invalid parameters for task:")

        LOGGER.debug("Building C# project for Windows")

        if Platform.get_system_platform() != TargetPlatform.WINDOWS:
            raise Exception(f"This task can only be executed on Windows systems (current platform: {Platform.get_system_platform()})")

        msbuild_path = parameters.get("msbuild_path", None)
        project_file = parameters.get("project_file", None)
        build_type = parameters.get("build_type", "Release")
        additional_args = parameters.get("additional_args", [])
        additional_env = parameters.get("additional_env", {})
        build_constants = parameters.get("build_constants", None)

        if not msbuild_path.exists() or not msbuild_path.is_file():
            LOGGER.error(f"msbuild_path ({msbuild_path.absolute()} is invalid")
            msbuild_path = None

        if msbuild_path is None:
            LOGGER.debug("No msbuild path specified, using default")
            msbuild_path = Path(f"C:{os.pathsep}{os.pathsep}Program Files (x86){os.pathsep}Microsoft Visual Studio")

            if not msbuild_path.exists() or not msbuild_path.is_dir():
                LOGGER.error(f"Microsoft Visual Studio installation not found at {msbuild_path.absolute()}")
                return TaskOutput(success=False)

            installations = sorted([x for x in msbuild_path.iterdir() if x.is_dir()], reverse=True)

            if len(installations) == 0:
                LOGGER.error(f"No Microsoft Visual Studio installations at {msbuild_path.absolute()}")
                return TaskOutput(success=False)

            found = False
            for installation in installations:
                msbuild_path = installation / "MSBuild" / "Current" / "Bin" / "MSBuild.exe"
                if msbuild_path.exists() and msbuild_path.is_file():
                    found = True
                    LOGGER.debug(f"Found MSBuild at {msbuild_path.absolute()}")
                    break

            if not found:
                LOGGER.error(f"No MSBuild installation found")
                return TaskOutput(success=False)

        if not project_file.exists() or not project_file.is_file() or project_file.suffix != ".csproj":
            LOGGER.error(f"Project file ({project_file.absolute()} is invalid")
            return TaskOutput(success=False)

        if project_file is None:
            LOGGER.debug("No project file specified, using default")

            found = False
            for file in build_directory.iterdir():
                if file.exists() and file.is_file() and file.suffix == ".csproj":
                    project_file = file
                    if not found:
                        found = True
                    else:
                        LOGGER.error(f"Multiple project files found in {build_directory.absolute()}")
                        return TaskOutput(success=False)

        build_args = [
            f"{project_file.absolute()}",
            f"-property:Configuration={build_type}",
            "-t:build",
            "-restore",
        ]

        if build_constants is not None:
            build_args.append(f"-property:DefineConstants=\"{';'.join(build_constants)}\"")

        build_env = os.environ.copy()
        for k, v in additional_env:
            build_env[k] = v

        sys.stdout.flush()
        sys.stderr.flush()
        result = subprocess.run([msbuild_path.absolute(), *build_args, *additional_args],
                                cwd=build_directory.absolute(),
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                env=build_env)

        if result.returncode != 0:
            LOGGER.error(f"MSBuild failed with return code {result.returncode}")
            return TaskOutput(success=False)

        return TaskOutput(success=True)
