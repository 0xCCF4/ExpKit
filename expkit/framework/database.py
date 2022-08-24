from typing import Dict, Optional, Type

from expkit.base.stage import StageTaskTemplate



def register_task(task: Type[StageTaskTemplate], *nargs, **kwargs):
    TaskDatabase.get_instance().add_task(task(*nargs, **kwargs))


class TaskDatabase():
    def __init__(self):
        self.tasks: Dict[str, StageTaskTemplate] = {}

    def add_task(self, task: StageTaskTemplate):
        assert task.name == task.name.lower(), "Only lower case task names are allowed"
        if task.name in self.tasks:
            raise ValueError(f"Task with name {task.name} already exists in the database")
        self.tasks[task.name.upper()] = task

    def get_task(self, name: str) -> Optional[StageTaskTemplate]:
        return self.tasks.get(name, None)

    __instance: 'TaskDatabase' = None
    @staticmethod
    def get_instance() -> 'TaskDatabase':
        if TaskDatabase.__instance is None:
            TaskDatabase.__instance = TaskDatabase()
        return TaskDatabase.__instance


class StageDatabase():
    pass
