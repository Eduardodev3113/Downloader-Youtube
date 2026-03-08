import yt_dlp
import os

pastaAtual = os.getcwd()

def baixar(url, pasta, opcao, barra, nome):
    if not nome:
        nome = "%(title)s"
    with yt_dlp.YoutubeDL({}) as ydl:
        info = ydl.extract_info(url, download=False)
        titulo = info["title"]
    def progresso(d):
        if d["status"] == "downloading":
            if d.get("total_bytes"):
                percentual = d["downloaded_bytes"] / d["total_bytes"]
            barra.set(percentual)
        return
    if opcao == "1":
        ydl_opts = {
            "noplaylist": True,
            "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]",
            "outtmpl": os.path.join(pasta, f"{nome}.%(ext)s"),
            "merge_output_format": "mp4",
            "progress_hooks": [progresso],
        }
    elif opcao == "2":
        ydl_opts = {
            "noplaylist": True,
            "format": "bestaudio/best",
            "outtmpl": os.path.join(pasta, f"{nome}.%(ext)s"),
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
            "progress_hooks": [progresso],
        }]
    }
    elif opcao == "3":
        ydl_opts = {
            "noplaylist": True,
            "format": "bestaudio/best",
            "outtmpl": os.path.join(pasta, f"{nome}.%(ext)s"),
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "wav",
            "progress_hooks": [progresso],
        }]
    }


    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
        return titulo