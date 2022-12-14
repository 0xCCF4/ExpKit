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


@auto_stage_group("TEMPLATE_ENGINE", "A template engine that can be used to modify and generate source code.")
@register_stage
class TextTemplateEngine(StageTemplate):
    def __init__(self):
        super().__init__(
            name="stages.templating.text_template_engine",
            description="A stage that uses a text template engine to transform strings.",
            platform=TargetPlatform.ALL,
            required_parameters=[
                ("TPL_VARIABLES", Dict[str, str], "A mapping of regex patterns and corresponding replacements"),
                ("TPL_EXTENSIONS", Optional[List[str]], "A list of file extensions on which replacements should be transformed on (default: common source code extensions)")
            ]
        )

        self.add_task("tasks.general.utils.untar_folder")
        self.add_task("tasks.obfuscation.csharp.string_transform_template")
        self.add_task("tasks.general.utils.tar_folder")

        assert len(self.tasks) == 0 or len(self.tasks) == 3

    def prepare_build(self, context: StageContext):
        super().prepare_build(context)

        extensions = context.parameters.get("TPL_EXTENSIONS", None)
        if extensions is None:
            extensions = ["cs", "csproj", "sln", "c", "cpp", "h", "hpp", "txt", "md", "json", "xml", "yml", "yaml",
                          "asm", "s", "ps1", "psm1"]
        else:
            LOGGER.debug("Using custom file extension list for template engine:")
            for extension in extensions:
                LOGGER.debug(f" - .{extension}")

        context.set("TPL_EXTENSIONS", extensions)
        context.set("TPL_VARIABLES", context.parameters.get("TPL_VARIABLES", {}))

    def execute_task(self, context: StageContext, index: int, task: TaskTemplate):
        task_parameters = {}

        if task.name == "tasks.general.utils.untar_folder":
            task_parameters["folder"] = context.build_directory
            task_parameters["tarfile"] = context.initial_payload.get_content()

            status = task.execute(task_parameters, context.build_directory, self)

            if not status.success:
                raise Exception("Failed to untar folder.")

        elif task.name == "task.obfuscation.csharp.string_transform_template":
            extensions = context.get("TPL_EXTENSIONS")

            files = []
            recursive_foreach_file(context.build_directory, lambda f: files.append(f))
            transform_params = []

            LOGGER.debug("Running template engine on files:")
            for file in files:
                if (len(file.suffix) == 0 and "" in extensions) or file.suffix[1:] in extensions:
                    LOGGER.debug(f" - {file}")
                    transform_params.append((file, file))
                else:
                    LOGGER.debug(f" - [SKIP] {file}")

            task_parameters["files"] = transform_params
            task_parameters["replacements"] = context.get("TPL_VARIABLES", {})

            status = task.execute(task_parameters, context.build_directory, self)

            if not status.success:
                raise Exception("Failed to transform strings.")

        elif task.name == "tasks.general.utils.tar_folder":
            task_parameters["folder"] = context.build_directory

            status = task.execute(task_parameters, context.build_directory, self)

            if not status.success:
                raise Exception("Failed to tar folder.")

            assert isinstance(status, TarTaskOutput)

            context.set("output", status.data)

    def finish_build(self, context: StageContext) -> Payload:
        assert context.get("output") is not None

        return context.initial_payload.copy(
            type=PayloadType.CSHARP_PROJECT,
            content=context.get("output"))

    def get_supported_input_payload_types(self) -> List[PayloadType]:
        return [t for t in PayloadType.get_all_types(include_empty=False) if (t.is_file() and not t.is_binary()) or t.is_project()]

    def get_output_payload_type(self, input: PayloadType, dependencies: List[PayloadType]) -> List[PayloadType]:
        return [input] if (input.is_file() and not input.is_binary()) or input.is_project() else []
