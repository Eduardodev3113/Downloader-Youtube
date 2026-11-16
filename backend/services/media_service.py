from pathlib import Path

from .common import require_tool, run_command

VIDEO = {"mp4", "mkv", "mov", "avi", "webm", "gif"}
AUDIO = {"mp3", "wav", "flac", "m4a", "opus", "ogg", "aac", "aiff"}


def convert(source: Path, target: str, output: Path, options: dict) -> None:
    ffmpeg = require_tool("ffmpeg")
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
    if options.get("extract_frames"):
        fps = min(60, max(0.1, float(options.get("fps", 1))))
        args += ["-vf", f"fps={fps}", str(output / "frame-%05d.png")]
    elif target == "gif":
        fps = min(60, max(1, int(options.get("fps", 15))))
        scale = min(1920, max(64, int(options.get("width", 640))))
        args += ["-vf", f"fps={fps},scale={scale}:-1:flags=lanczos", str(output)]
    elif options.get("compress_mb"):
        target_bytes = max(1, float(options["compress_mb"])) * 1024 * 1024
        duration = max(1, float(options.get("duration", 60)))
        audio_kbps = min(320, max(64, int(options.get("audio_kbps", 128))))
        video_kbps = max(100, int((target_bytes * 8 / duration / 1000) - audio_kbps))
        args += ["-c:v", "libx264", "-b:v", f"{video_kbps}k", "-pass", "1",
                 "-passlogfile", str(output.with_suffix(".pass")), "-an", "-f", "null", "NUL" if __import__("os").name == "nt" else "/dev/null"]
        run_command(args)
        args = [ffmpeg, "-hide_banner", "-y", "-i", str(source), "-c:v", "libx264",
                "-b:v", f"{video_kbps}k", "-pass", "2", "-passlogfile",
                str(output.with_suffix(".pass")), "-c:a", "aac", "-b:a",
                f"{audio_kbps}k", str(output)]
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
            args += ["-c:v", "libx264", "-preset", "medium", "-crf", str(min(35, max(18, int(options.get("quality", 23)))))]
            if target == "webm":
                args[-4:] = ["-c:v", "libvpx-vp9", "-crf", "32", "-b:v", "0"]
        args += [str(output)]

    run_command(args)
