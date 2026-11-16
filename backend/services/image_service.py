from pathlib import Path
from io import BytesIO

from PIL import Image, ImageOps

from .common import require_tool, run_command

IMAGE_FORMATS = {"png", "jpg", "jpeg", "webp", "avif", "ico", "bmp", "tiff"}


def convert(source: Path, target: str, output: Path, options: dict) -> None:
    if source.suffix.lower() == ".svg":
        import cairosvg
        rendered = cairosvg.svg2png(url=str(source), output_width=options.get("width"))
        with Image.open(BytesIO(rendered)) as image:
            _save(image, target, output, options)
        return
    with Image.open(source) as image:
        image = ImageOps.exif_transpose(image)
        if options.get("remove_background"):
            from rembg import remove
            image = remove(image)
        width = options.get("width")
        height = options.get("height")
        if width or height:
            width = max(1, int(width or image.width))
            height = max(1, int(height or image.height))
            image.thumbnail((width, height), Image.Resampling.LANCZOS)
        if options.get("upscale"):
            image = image.resize((image.width * 2, image.height * 2), Image.Resampling.LANCZOS)
        _save(image, target, output, options)


def _save(image: Image.Image, target: str, output: Path, options: dict) -> None:
    fmt = "JPEG" if target in ("jpg", "jpeg") else target.upper()
    if fmt in ("JPEG", "BMP") and image.mode not in ("RGB", "L"):
        image = image.convert("RGB")
    kwargs = {"quality": min(100, max(1, int(options.get("quality", 85))))}
    if fmt == "JPEG":
        kwargs["optimize"] = True
    if fmt == "ICO":
        image.save(output, format=fmt, sizes=[(256, 256)])
    else:
        image.save(output, format=fmt, **(kwargs if fmt in ("JPEG", "WEBP", "AVIF") else {}))
