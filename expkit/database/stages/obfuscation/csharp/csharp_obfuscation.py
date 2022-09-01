from expkit.base.architecture import TargetPlatform
from expkit.base.stage import StageTemplate
from expkit.framework.database import register_stage, TaskDatabase


@register_stage
class CSharpObfuscationAll(StageTemplate):
    def __init__(self):
        super().__init__(
            name="stages.obfuscation.csharp.csharp_obfuscation",
            description="Obfuscates CSharp source code to prevent signature detection.",
            platform=TargetPlatform.ALL,
            required_parameters={}
        )

        self.__status: int = 0
        self.tasks.append(TaskDatabase.get_instance().get_task("task.obfuscation.csharp.string_transform_template"))