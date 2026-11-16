import re
import shutil
import subprocess
import yt_dlp
import os
import sys


_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def limpar_ansi(texto):
    """Remove códigos de cor ANSI que o yt-dlp injeta nas mensagens de erro
    (aparecem como '[0;31m...[0m' quando o texto vira string crua)."""
    return _ANSI_RE.sub("", str(texto)).strip()


def encontrar_ffmpeg():
    """Procura por ffmpeg em locais comuns do Windows."""
    caminhos_comuns = [
        # Se foi instalado com ffmpeg-python ou similar
        os.path.join(os.getenv("LOCALAPPDATA", ""), "ffmpeg", "bin", "ffmpeg.exe"),
        os.path.join(os.getenv("APPDATA", ""), "ffmpeg", "bin", "ffmpeg.exe"),
        
        # Se foi instalado com choco ou winget em Program Files
        "C:\\Program Files\\ffmpeg\\bin\\ffmpeg.exe",
        "C:\\Program Files (x86)\\ffmpeg\\bin\\ffmpeg.exe",
        
        # Se foi instalado em C:\
        "C:\\ffmpeg\\bin\\ffmpeg.exe",
        
        # BuildExe (PyInstaller)
        os.path.join(os.getenv("MEIPASS", ""), "ffmpeg.exe") if hasattr(sys, "_MEIPASS") else None,
    ]
    
    # Remove None e caminhos inválidos
    caminhos_comuns = [c for c in caminhos_comuns if c and os.path.isfile(c)]
    
    # Tenta os caminhos comuns
    for caminho in caminhos_comuns:
        if ffmpeg_disponivel(caminho):
            print(f"✓ ffmpeg encontrado em: {caminho}")
            return caminho
    
    # Tenta ffmpeg no PATH
    if shutil.which("ffmpeg"):
        return "ffmpeg"
    
    return None


def ffmpeg_disponivel(ffmpeg_path):
    """Verifica se ffmpeg está disponível no sistema."""
    if not ffmpeg_path:
        return False
    
    # Primeiro tenta encontrar o arquivo
    if os.path.isfile(ffmpeg_path):
        try:
            subprocess.run([ffmpeg_path, "-version"], 
                          capture_output=True, 
                          timeout=2, 
                          check=True)
            return True
        except (subprocess.CalledProcessError, OSError, subprocess.TimeoutExpired):
            return False
    
    # Depois tenta shutil.which
    if shutil.which(ffmpeg_path) is not None:
        return True
    
    return False


def baixar(url, pasta, opcao, progress_callback, nome, qualidade="Melhor qualidade"):
    """
    Baixa um vídeo do YouTube com yt-dlp.

    progress_callback: função chamada com um float de 0.0 a 1.0 conforme
    o download avança. Antes era `barra.set(...)` de um CTkProgressBar;
    agora é desacoplado da interface para poder alimentar tanto uma
    barra do Tkinter quanto o medidor da interface web.
    """
    # Tenta encontrar ffmpeg automaticamente
    ffmpeg_path = encontrar_ffmpeg()

    if not ffmpeg_path:
        raise RuntimeError(
            "❌ ffmpeg não foi encontrado!\n\n"
            "Para instalar:\n"
            "• Windows: winget install ffmpeg (ou choco install ffmpeg)\n"
            "• Mac: brew install ffmpeg\n"
            "• Linux: sudo apt install ffmpeg\n\n"
            "Depois de instalar:\n"
            "1. Reinicie o terminal ou computador\n"
            "2. Teste: ffmpeg -version\n"
            "3. Abra o app novamente"
        )

    if not nome:
        nome = "%(title)s"

    with yt_dlp.YoutubeDL({}) as ydl:
        info = ydl.extract_info(url, download=False)
        titulo = info["title"]

    def progresso(d):
        if d["status"] == "downloading":
            if d.get("total_bytes"):
                percentual = d["downloaded_bytes"] / d["total_bytes"]
                if progress_callback:
                    progress_callback(percentual)
        return

    if qualidade == "Melhor qualidade":
        formato_mp4 = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]"
    else:
        altura = qualidade.replace("p", "")
        formato_mp4 = f"bestvideo[height<={altura}][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]"

    opts_base = {"noplaylist": True, "quiet": True, "no_color": True, "ffmpeg_location": ffmpeg_path}

    if opcao == "1":
        ydl_opts = {
            **opts_base,
            "format": formato_mp4,
            "outtmpl": os.path.join(pasta, f"{nome}.%(ext)s"),
            "merge_output_format": "mp4",
            "progress_hooks": [progresso],
        }
    elif opcao == "2":
        ydl_opts = {
            **opts_base,
            "format": "bestaudio/best",
            "outtmpl": os.path.join(pasta, f"{nome}.%(ext)s"),
            "progress_hooks": [progresso],
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
            }],
        }
    elif opcao == "3":
        ydl_opts = {
            **opts_base,
            "format": "bestaudio/best",
            "outtmpl": os.path.join(pasta, f"{nome}.%(ext)s"),
            "progress_hooks": [progresso],
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "wav",
            }],
        }
    else:
        raise ValueError(f"Formato inválido: {opcao}")

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
    except Exception as e:
        raise RuntimeError(limpar_ansi(e)) from None

    if progress_callback:
        progress_callback(1.0)
    return titulo

    if not nome:
        nome = "%(title)s"

    with yt_dlp.YoutubeDL({}) as ydl:
        info = ydl.extract_info(url, download=False)
        titulo = info["title"]

    def progresso(d):
        if d["status"] == "downloading":
            if d.get("total_bytes"):
                percentual = d["downloaded_bytes"] / d["total_bytes"]
                if progress_callback:
                    progress_callback(percentual)
        return

    if qualidade == "Melhor qualidade":
        formato_mp4 = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]"
    else:
        altura = qualidade.replace("p", "")
        formato_mp4 = f"bestvideo[height<={altura}][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]"

    opts_base = {"noplaylist": True, "quiet": True, "no_color": True, "ffmpeg_location": ffmpeg_path}

    if opcao == "1":
        ydl_opts = {
            **opts_base,
            "format": formato_mp4,
            "outtmpl": os.path.join(pasta, f"{nome}.%(ext)s"),
            "merge_output_format": "mp4",
            "progress_hooks": [progresso],
        }
    elif opcao == "2":
        ydl_opts = {
            **opts_base,
            "format": "bestaudio/best",
            "outtmpl": os.path.join(pasta, f"{nome}.%(ext)s"),
            "progress_hooks": [progresso],
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
            }],
        }
    elif opcao == "3":
        ydl_opts = {
            **opts_base,
            "format": "bestaudio/best",
            "outtmpl": os.path.join(pasta, f"{nome}.%(ext)s"),
            "progress_hooks": [progresso],
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "wav",
            }],
        }
    else:
        raise ValueError(f"Formato inválido: {opcao}")

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
    except Exception as e:
        raise RuntimeError(limpar_ansi(e)) from None

    if progress_callback:
        progress_callback(1.0)
    return titulo
