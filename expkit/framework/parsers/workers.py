import json
from pathlib import Path


class WorkerConfig:
    def __init__(self, content: dict|str|Path):
        if isinstance(content, Path):
            content = content.read_text()

        if isinstance(content, dict):
            content = json.dumps(content)

        if isinstance(content, str):
            content = json.loads(content)
        else:
            raise TypeError(f"Invalid type for content: {type(content)}")

        self.content = content

    def parse(self):
        pass
