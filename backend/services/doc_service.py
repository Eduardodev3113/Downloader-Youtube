import subprocess
from pathlib import Path

import fitz
from PIL import Image

from .common import require_tool, run_command

DOC_FORMATS = {"pdf", "docx", "txt", "md", "html", "png", "jpg", "jpeg"}


def convert(source: Path, target: str, output: Path, options: dict) -> None:
    suffix = source.suffix.lower()
    if suffix == ".pdf":
        document = fitz.open(source)
        if target in ("txt", "md"):
            output.write_text("\n\n".join(page.get_text() for page in document), encoding="utf-8")
        elif target in ("png", "jpg", "jpeg"):
            for index, page in enumerate(document):
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
                pix.save(output.with_name(f"{output.stem}-{index + 1}.{target}"))
        elif target == "pdf":
            if options.get("compress"):
                document.save(output, garbage=4, deflate=True, clean=True)
            else:
                raise ValueError("O arquivo já está em PDF.")
        else:
            _libreoffice(source, target, output.parent)
    elif target == "pdf" and suffix in (".png", ".jpg", ".jpeg"):
        image = Image.open(source).convert("RGB")
        image.save(output, "PDF", resolution=150)
    elif suffix in (".md", ".txt") and target in ("pdf", "html", "docx"):
        pandoc = require_tool("pandoc")
        run_command([pandoc, str(source), "-o", str(output)])
    else:
        _libreoffice(source, target, output.parent)


def _libreoffice(source: Path, target: str, directory: Path) -> None:
    executable = require_tool("soffice")
    run_command([executable, "--headless", "--convert-to", target, "--outdir", str(directory), str(source)])
    generated = directory / f"{source.stem}.{target}"
    if not generated.exists():
        raise RuntimeError(f"LibreOffice não gerou o arquivo {generated.name}.")
