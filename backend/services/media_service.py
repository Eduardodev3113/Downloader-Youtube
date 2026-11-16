import json
import subprocess
from pathlib import Path

from .common import require_tool, run_command

VIDEO = {"mp4", "mkv", "mov", "avi", "webm", "gif"}
AUDIO = {"mp3", "wav", "flac", "m4a", "opus", "ogg", "aac", "aiff"}


def convert(source: Path, target: str, output: Path, options: dict) -> None:
    ffmpeg = require_tool("ffmpeg")
    if options.get("extract_frames"):
        output.mkdir(parents=True, exist_ok=True)
        fps = min(60, max(0.1, float(options.get("fps", 1))))
        run_command([ffmpeg, "-hide_banner", "-y", "-i", str(source), "-vf",
                     f"fps={fps}", str(output / "frame-%05d.png")])
        return
    args = [ffmpeg, "-hide_banner", "-y", "-i", str(source)]
    start, end = options.get("start"), options.get("end")
    if start is not None:
        args += ["-ss", str(max(0, float(start)))]
    if end is not None:
        duration = float(end) - float(start or 0)
        if duration <= 0:
            raise ValueError("O horário final deve ser posterior ao inicial.")
        args += ["-t", str(duration)]

    if options.get("mute"):
        args += ["-an"]
    if target == "gif":
        fps = min(60, max(1, int(options.get("fps", 15))))
        scale = min(1920, max(64, int(options.get("width", 640))))
        args += ["-vf", f"fps={fps},scale={scale}:-1:flags=lanczos", str(output)]
    elif options.get("compress_mb"):
        target_bytes = max(1, float(options["compress_mb"])) * 1024 * 1024
        duration = float(options.get("duration") or _duration(source))
        if duration <= 0:
            raise ValueError("Não foi possível determinar a duração para calcular o tamanho-alvo.")
        audio_kbps = min(320, max(64, int(options.get("audio_kbps", 128))))
        video_kbps = max(100, int((target_bytes * 8 / duration / 1000) - audio_kbps))
        codec = "h264_nvenc" if options.get("gpu") else "libx264"
        pass_args = [] if options.get("gpu") else ["-passlogfile", str(output.with_suffix(".pass"))]
        trim_args = []
        if start is not None:
            trim_args += ["-ss", str(max(0, float(start)))]
        if end is not None:
            trim_args += ["-t", str(float(end) - float(start or 0))]
        common = [ffmpeg, "-hide_banner", "-y", *trim_args, "-i", str(source),
                  "-c:v", codec, "-b:v", f"{video_kbps}k", *pass_args]
        null_output = "NUL" if __import__("os").name == "nt" else "/dev/null"
        first_pass = common + (["-pass", "1"] if not options.get("gpu") else []) + [
            "-an", "-f", "null", null_output]
        run_command(first_pass)
        args = common + (["-pass", "2"] if not options.get("gpu") else []) + [
            "-c:a", "aac", "-b:a", f"{audio_kbps}k", str(output)]
    else:
        if target in AUDIO:
            args += ["-vn"]
            if target == "mp3":
                bitrate = min(320, max(128, int(options.get("bitrate", 320))))
                args += ["-b:a", f"{bitrate}k"]
            if options.get("normalize"):
                args += ["-af", "loudnorm=I=-16:TP=-1.5:LRA=11"]
        if options.get("copy"):
            args += ["-c", "copy"]
        elif target in VIDEO and target != "gif":
            codec = "h264_nvenc" if options.get("gpu") else "libx264"
            args += ["-c:v", codec]
            if target == "webm":
                args += ["-crf", "32", "-b:v", "0"]
            elif options.get("gpu"):
                args += ["-preset", "p5", "-cq", str(min(35, max(18, int(options.get("quality", 23)))))]
            else:
                args += ["-preset", "medium", "-crf", str(min(35, max(18, int(options.get("quality", 23)))))]
        args += [str(output)]

    run_command(args)


def _duration(source: Path) -> float:
    ffprobe = require_tool("ffprobe")
    result = subprocess.run([ffprobe, "-v", "error", "-show_entries", "format=duration",
                             "-of", "json", str(source)], capture_output=True, text=True,
                            timeout=30, check=False)
    if result.returncode:
        raise RuntimeError((result.stderr or "ffprobe falhou ao ler a duração.").strip())
    return float(json.loads(result.stdout)["format"]["duration"])
