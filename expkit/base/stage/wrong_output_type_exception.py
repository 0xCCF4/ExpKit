from typing import Optional

from expkit.base.stage.base import StageTemplate
from expkit.base.stage.context import StageContext
from expkit.base.utils.type_checking import type_guard


class SkipStageExecution(Exception):
    """Exception raised when the target output-type of a stage can not be produced using the current context."""

    #@type_guard
    def __init__(self, message: str, context: Optional[StageContext]=None):
        super().__init__(message)
        self.message = message
        self.context = context
