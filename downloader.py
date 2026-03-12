import yt_dlp
import os
import sys

pastaAtual = os.getcwd()

def baixar(url, pasta, opcao, barra, nome, qualidade="Melhor qualidade"):
    
    if hasattr(sys, '_MEIPASS'):
        ffmpeg_path = os.path.join(sys._MEIPASS, "ffmpeg.exe")
    else:
        ffmpeg_path = "ffmpeg" 
    
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

    # monta o formato baseado na qualidade escolhida
    if qualidade == "Melhor qualidade":
        formato_mp4 = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]"
    else:
        altura = qualidade.replace("p", "")
        formato_mp4 = f"bestvideo[height<={altura}][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]"

    if opcao == "1":
        ydl_opts = {
            "noplaylist": True,
            "format": formato_mp4,
            "outtmpl": os.path.join(pasta, f"{nome}.%(ext)s"),
            "merge_output_format": "mp4",
            "progress_hooks": [progresso],
            "ffmpeg_location": ffmpeg_path
        }
    elif opcao == "2":
        ydl_opts = {
            "noplaylist": True,
            "ffmpeg_location": ffmpeg_path,
            "format": "bestaudio/best",
            "outtmpl": os.path.join(pasta, f"{nome}.%(ext)s"),
            "progress_hooks": [progresso],
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
            }]
            
        }
    elif opcao == "3":
        ydl_opts = {
            "noplaylist": True,
            "ffmpeg_location": ffmpeg_path,
            "format": "bestaudio/best",
            "outtmpl": os.path.join(pasta, f"{nome}.%(ext)s"),
            "progress_hooks": [progresso],
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "wav",
                
            }]
        }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
        return titulo
