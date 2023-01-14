from pathlib import Path
from typing import List, Callable


def recursive_foreach_file(root: Path, func_foreach_file: Callable[[Path], None], func_recurse_directory: Callable[[Path], bool] = None, follow_symlinks: bool = False):
    files: List[Path] = [root]

    if func_recurse_directory is None:
        func_recurse_directory = lambda x: True

    while len(files) > 0:
        file = files.pop()

        if not file.exists():
            raise FileNotFoundError(f"File {file} does not exist")

        if file.is_symlink() and not follow_symlinks:
            continue

        if file.is_symlink() and follow_symlinks:
            file = file.resolve()
            files.append(file)
            continue

        if file.is_dir() and func_recurse_directory(file):
            for child in file.iterdir():
                files.append(child)
            continue

        if file.is_dir() and not func_recurse_directory(file):
            continue

        if file.is_file():
            func_foreach_file(file)
            continue

        raise ValueError(f"Unknown file type {file}")
