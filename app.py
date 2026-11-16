import json
import os
import subprocess
import sys
import threading

import webview
import yt_dlp

from downloader import baixar, limpar_ansi
from historico import carregar_historico, limpar_historico, salvar_download


def resource_path(file):
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, file)
    return os.path.abspath(file)


class Api:
    """Tudo que o JS pode chamar via window.pywebview.api.<metodo>(...)."""

    def __init__(self):
        self.window = None

    def set_window(self, window):
        self.window = window

    def _emit(self, event, payload=None):
        """Empurra um evento pro JS (usado pro progresso do download)."""
        if not self.window:
            return
        data = json.dumps(payload if payload is not None else {})
        self.window.evaluate_js(f"window.__deck.emit('{event}', {data})")

    # ---------- Downloader ----------

    def buscar_info(self, url):
        """Busca info em thread separada para não bloquear UI."""
        def worker():
            try:
                with yt_dlp.YoutubeDL({"quiet": True, "no_color": True}) as ydl:
                    info = ydl.extract_info(url, download=False)

                qualidades = []
                for f in info.get("formats", []):
                    if f.get("height"):
                        q = f"{f['height']}p"
                        if q not in qualidades:
                            qualidades.append(q)
                qualidades.sort(key=lambda x: int(x.replace("p", "")), reverse=True)
                if not qualidades:
                    qualidades = ["Melhor qualidade"]

                self._emit("buscar_info_done", {
                    "ok": True,
                    "titulo": info.get("title", ""),
                    "thumbnail": info.get("thumbnail", ""),
                    "duracao": info.get("duration") or 0,
                    "canal": info.get("uploader", ""),
                    "qualidades": qualidades,
                })
            except Exception as e:
                self._emit("buscar_info_done", {"ok": False, "erro": limpar_ansi(e)})

        threading.Thread(target=worker, daemon=True).start()
        return {"ok": True}  # Retorna imediatamente

    def iniciar_download(self, url, pasta, formato, nome, qualidade):
        if not url or not pasta:
            return {"ok": False, "erro": "Informe a URL e a pasta de destino."}

        def worker():
            try:
                def progresso(p):
                    self._emit("download_progress", {"percentual": p})

                titulo = baixar(url, pasta, formato, progresso, nome, qualidade)
                salvar_download(titulo, formato, pasta)
                self._emit("download_done", {"ok": True, "titulo": titulo})
            except Exception as e:
                self._emit("download_done", {"ok": False, "erro": limpar_ansi(e)})

        threading.Thread(target=worker, daemon=True).start()
        return {"ok": True}

    # ---------- Conversor ----------

    def converter(self, caminho, formato):
        """Converte arquivo em thread separada para não bloquear UI."""
        def worker():
            try:
                extensoes = {"1": ".mp4", "2": ".mp3", "3": ".wav"}
                ext_saida = extensoes.get(formato)
                if not ext_saida:
                    self._emit("converter_done", {"ok": False, "erro": "Formato inválido."})
                    return

                ext_original = os.path.splitext(caminho)[1]
                if ext_original == ext_saida:
                    self._emit("converter_done", {"ok": False, "erro": "O arquivo já está nesse formato."})
                    return

                saida = os.path.splitext(caminho)[0] + ext_saida
                subprocess.run(["ffmpeg", "-y", "-i", caminho, saida], check=True)

                nome = os.path.splitext(os.path.basename(caminho))[0]
                salvar_download(nome, formato, os.path.dirname(caminho))
                self._emit("converter_done", {"ok": True, "saida": saida})
            except Exception as e:
                self._emit("converter_done", {"ok": False, "erro": limpar_ansi(e)})

        threading.Thread(target=worker, daemon=True).start()
        return {"ok": True}  # Retorna imediatamente

    # ---------- Sistema de arquivos ----------

    def escolher_pasta(self):
        result = self.window.create_file_dialog(webview.FOLDER_DIALOG)
        return result[0] if result else ""

    def escolher_arquivo(self):
        result = self.window.create_file_dialog(webview.OPEN_DIALOG)
        return result[0] if result else ""

    def abrir_pasta(self, caminho):
        try:
            if not caminho:
                return {"ok": False, "erro": "Nenhum caminho definido."}
            alvo = os.path.dirname(caminho) if os.path.isfile(caminho) else caminho
            if sys.platform == "win32":
                os.startfile(alvo)
            elif sys.platform == "darwin":
                subprocess.run(["open", alvo])
            else:
                subprocess.run(["xdg-open", alvo])
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "erro": str(e)}

    # ---------- Histórico ----------

    def carregar_historico(self):
        return carregar_historico()

    def limpar_historico(self):
        limpar_historico()
        return {"ok": True}


def main():
    api = Api()
    window = webview.create_window(
        "YT / Deck",
        resource_path("web/index.html"),
        js_api=api,
        width=1000,
        height=700,
        min_size=(860, 600),
        background_color="#17181A",
    )
    api.set_window(window)
    webview.start()


if __name__ == "__main__":
    main()
