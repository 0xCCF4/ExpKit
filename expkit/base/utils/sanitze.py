import re

def sanitize_file_name(name: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_-]", "_", name)
