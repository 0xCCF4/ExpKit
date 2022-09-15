import importlib
import os
from pathlib import Path
from typing import List

from expkit.base.utils.files import recursive_foreach_file
from expkit.framework.database import auto_discover_databases, build_databases, reset_databases
from expkit.docs.utils import get_macros


def define_env(env):
    expkit_dir = Path(__file__).parent.parent

    reset_databases()

    auto_discover_databases(expkit_dir)
    external_dbs = os.environ.get("EXPKIT_DB", None)
    if external_dbs is not None:
        external_dbs = external_dbs.split(":")
        for db_config in external_dbs:
            db_config = db_config.split("#")
            if len(db_config) != 2:
                print(f"Invalid database configuration: {db_config}")
                continue

            path, module = db_config
            path = Path(path)

            print(f"Loading external database: {path} ({module})")
            if not path.exists() or not path.is_dir():
                print(f"Invalid database path: {path}")
            else:
                auto_discover_databases(path, module)

    build_databases()

    files: List[Path] = []
    recursive_foreach_file(expkit_dir / "docs" / "macros", lambda x: files.append(x), lambda x: x.name != "__pycache__", False)

    for file in files:
        if not file.name.startswith("_") and file.suffix == ".py":
            print(f"Discovering macros in {file.relative_to(expkit_dir)}")
            module = importlib.import_module(f"expkit.{(file.relative_to(expkit_dir)).as_posix().replace('/', '.')[:-3]}")
            importlib.reload(module)

    for k, v in get_macros().items():
        print(f"Registering macro: {k}")
        env.macro(v, name=k)
