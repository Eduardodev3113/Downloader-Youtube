import re
import shutil
import subprocess
from pathlib import Path

SAFE_STEM = re.compile(r"[^A-Za-z0-9._ -]+")


def safe_stem(value: str) -> str:
    stem = SAFE_STEM.sub("", Path(value).stem).strip(" .-_")
    return (stem or "converted")[:120]


def require_tool(name: str) -> str:
    executable = shutil.which(name)
    if not executable:
        raise RuntimeError(f"{name} não está instalado ou não está no PATH.")
    return executable


def run_command(args: list[str], *, timeout: int = 3600) -> None:
    result = subprocess.run(args, capture_output=True, text=True, timeout=timeout, check=False)
    if result.returncode:
        detail = (result.stderr or result.stdout or "Falha no processamento.").strip()
        raise RuntimeError(detail[-4000:])
