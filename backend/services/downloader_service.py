import ipaddress
import socket
from pathlib import Path
from urllib.parse import urlparse

import yt_dlp

from .common import safe_stem

ALLOWED_HOSTS = (
    "youtube.com", "youtu.be", "youtube-nocookie.com", "instagram.com", "tiktok.com",
    "twitter.com", "x.com", "soundcloud.com", "twitch.tv", "reddit.com",
)


def validate_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise ValueError("Informe uma URL http(s) válida de um serviço suportado.")
    host = parsed.hostname.lower().rstrip(".")
    if not any(host == domain or host.endswith("." + domain) for domain in ALLOWED_HOSTS):
        raise ValueError("Esse domínio ainda não está habilitado para downloads.")
    try:
        addresses = [ipaddress.ip_address(host)]
    except ValueError:
        try:
            addresses = [ipaddress.ip_address(entry[4][0]) for entry in socket.getaddrinfo(host, None)]
        except socket.gaierror as exc:
            raise ValueError("Não foi possível resolver o domínio informado.") from exc
    if any(not address.is_global for address in addresses):
        raise ValueError("URLs para endereços locais ou privados não são permitidas.")


def download(url: str, destination: Path, options: dict, progress) -> Path:
    validate_url(url)
    destination.mkdir(parents=True, exist_ok=True)
    template = str(destination / "%(title).120B.%(ext)s")
    out_opts = {
        "outtmpl": template, "quiet": True, "no_warnings": True,
        "noplaylist": not options.get("playlist", False), "progress_hooks": [progress],
        "restrictfilenames": True,
    }
    if options.get("start") is not None and options.get("end") is not None:
        out_opts["download_ranges"] = yt_dlp.utils.download_range_func(
            None, [(float(options["start"]), float(options["end"]))]
        )
        out_opts["force_keyframes_at_cuts"] = True
    if options.get("subtitles"):
        out_opts.update({"writesubtitles": True, "writeautomaticsub": True,
                         "subtitlesformat": options.get("subtitle_format", "srt")})
    if options.get("thumbnail"):
        out_opts.update({
            "writethumbnail": True,
            "postprocessors": [{"key": "FFmpegThumbnailsConvertor", "format": "jpg"}],
        })
    audio = options.get("audio_format")
    if audio:
        out_opts["format"] = "bestaudio/best"
        out_opts["postprocessors"] = [{
            "key": "FFmpegExtractAudio", "preferredcodec": audio,
            "preferredquality": str(options.get("bitrate", 320)),
        }]
    else:
        out_opts.update({"format": options.get("format", "bestvideo*+bestaudio/best"),
                         "merge_output_format": options.get("container", "mp4")})
    with yt_dlp.YoutubeDL(out_opts) as ydl:
        ydl.download([url])
    outputs = [p for p in destination.iterdir() if p.is_file()]
    if not outputs:
        raise RuntimeError("O downloader não produziu arquivos.")
    return outputs[0]


def clean_title(value: str) -> str:
    return safe_stem(value)
