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
            text = "\n\n".join(page.get_text() for page in document)
            if options.get("ocr") and not text.strip():
                import subprocess
                from .common import require_tool, run_command
                executable = require_tool("tesseract")
                chunks = []
                for index, page in enumerate(document):
                    image_path = output.parent / f"ocr-{index + 1}.png"
                    page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False).save(image_path)
                    result = subprocess.run([executable, str(image_path), "stdout"],
                                            capture_output=True, text=True, timeout=300, check=False)
                    image_path.unlink(missing_ok=True)
                    if result.returncode:
                        raise RuntimeError((result.stderr or "Tesseract falhou.").strip())
                    chunks.append(result.stdout)
                text = "\n\n".join(chunks)
            output.write_text(text, encoding="utf-8")
        elif target in ("png", "jpg", "jpeg"):
            for index, page in enumerate(document):
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
                pix.save(output.with_name(f"{output.stem}-{index + 1}.{target}"))
        elif target == "pdf":
            if options.get("split"):
                start = max(1, int(options.get("page_start", 1)))
                end = min(len(document), int(options.get("page_end", len(document))))
                if end < start:
                    raise ValueError("Intervalo de páginas inválido.")
                for page_number in range(start, end + 1):
                    part = fitz.open()
                    part.insert_pdf(document, from_page=page_number - 1, to_page=page_number - 1)
                    part.save(output.with_name(f"{output.stem}-page-{page_number}.pdf"))
                    part.close()
            elif options.get("compress"):
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
