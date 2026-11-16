import customtkinter as ctk
from tkinter import filedialog
from downloader import baixar
import threading
import os
import subprocess
import yt_dlp
import requests
from PIL import Image
from io import BytesIO
from customtkinter import CTkImage
from historico import salvar_download, carregar_historico, limpar_historico
import sys



def apagar_historico():
    limpar_historico()
    ler_historico()

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

janela = ctk.CTk()
janela.title("YouTube Downloader")
janela.geometry("500x550")

def resource_path(file):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, file)
    return os.path.abspath(file)

janela.iconbitmap(resource_path("icone.ico"))

abas = ctk.CTkTabview(janela)
abas.pack(fill="both", expand=True)

abas.add("Downloader")
abas.add("Conversor")
abas.add("Histórico")

# ── ABA DOWNLOADER 
frame_down = ctk.CTkScrollableFrame(abas.tab("Downloader"), width=460, height=450)
frame_down.pack(fill="both", expand=True)

label_url = ctk.CTkLabel(frame_down, text="URL do vídeo:")
label_url.pack(pady=5)

campo_url = ctk.CTkEntry(frame_down, width=400)
campo_url.pack(pady=5)

btn_buscar = ctk.CTkButton(frame_down, text="Buscar", command=lambda: buscar_info())
btn_buscar.pack(pady=5)

label_thumb = ctk.CTkLabel(frame_down, text="")
label_thumb.pack(pady=5)

label_titulo_video = ctk.CTkLabel(frame_down, text="", wraplength=400)
label_titulo_video.pack(pady=2)

label_qualidade = ctk.CTkLabel(frame_down, text="Qualidade:")
label_qualidade.pack(pady=5)
qualidade_var = ctk.StringVar(value="Melhor qualidade")
menu_qualidade = ctk.CTkOptionMenu(frame_down, variable=qualidade_var, values=["Melhor qualidade"])
menu_qualidade.pack(pady=5)

def buscar_info():
    """Busca info do vídeo em thread separada para não bloquear UI."""
    btn_buscar.configure(state="disabled", text="Buscando...")
    label_titulo_video.configure(text="Buscando informações...")
    
    def thread_busca():
        try:
            url = campo_url.get()
            with yt_dlp.YoutubeDL({"quiet": True, "no_color": True}) as ydl:
                info = ydl.extract_info(url, download=False)
                thumb_url = info["thumbnail"]
                titulo = info["title"]
            
            # Baixa thumbnail com timeout
            try:
                img_data = requests.get(thumb_url, timeout=5).content
                img = Image.open(BytesIO(img_data)).resize((320, 180))
                ctk_img = CTkImage(img, size=(320, 180))
            except Exception as e:
                print(f"Erro ao baixar thumbnail: {e}")
                ctk_img = None
            
            qualidades = []
            for f in info.get("formats", []):
                if f.get("height"):
                    qualidade = f"{f['height']}p"
                    if qualidade not in qualidades:
                        qualidades.append(qualidade)
            qualidades.sort(key=lambda x: int(x.replace("p", "")), reverse=True)
            if not qualidades:
                qualidades = ["Melhor qualidade"]
            
            # Atualiza UI de forma thread-safe
            janela.after(0, lambda: _atualizar_info_ui(ctk_img, titulo, qualidades))
        except Exception as e:
            janela.after(0, lambda: _erro_busca(str(e)))
    
    thread = threading.Thread(target=thread_busca, daemon=True)
    thread.start()

def _atualizar_info_ui(ctk_img, titulo, qualidades):
    """Atualiza UI após busca bem-sucedida."""
    if ctk_img:
        label_thumb.configure(image=ctk_img, text="")
        label_thumb.image = ctk_img
    label_titulo_video.configure(text=titulo, text_color="white")
    menu_qualidade.configure(values=qualidades)
    qualidade_var.set(qualidades[0])
    btn_buscar.configure(state="normal", text="Buscar")

def _erro_busca(erro):
    """Mostra erro ao buscar."""
    label_titulo_video.configure(text=f"Erro: {erro}", text_color="red")
    btn_buscar.configure(state="normal", text="Buscar")

label_nome_arquivo = ctk.CTkLabel(frame_down, text="Nome do Arquivo:")
label_nome_arquivo.pack(pady=5)

campo_nome_arquivo = ctk.CTkEntry(frame_down, width=400)
campo_nome_arquivo.pack(pady=5)

label_pasta = ctk.CTkLabel(frame_down, text="Caminho para salvar:")
label_pasta.pack(pady=5)

def escolher_pasta():
    campo_pasta.delete(0, ctk.END)
    campo_pasta.insert(0, filedialog.askdirectory())

campo_pasta = ctk.CTkEntry(frame_down, width=400)
campo_pasta.pack(pady=5)

btn_pasta = ctk.CTkButton(frame_down, text="Escolher pasta", command=escolher_pasta)
btn_pasta.pack(pady=5)

label_formato = ctk.CTkLabel(frame_down, text="Formato:")
label_formato.pack(pady=5)

formato = ctk.StringVar(value="1")

ctk.CTkRadioButton(frame_down, text="MP4", variable=formato, value="1").pack(pady=2)
ctk.CTkRadioButton(frame_down, text="MP3", variable=formato, value="2").pack(pady=2)
ctk.CTkRadioButton(frame_down, text="WAV", variable=formato, value="3").pack(pady=2)

def abrir_pasta():
    os.startfile(campo_pasta.get())

btn_abrir_pasta = ctk.CTkButton(frame_down, text="Abrir Pasta", command=abrir_pasta)
btn_abrir_pasta.pack(pady=5)

def iniciar_download():
    barra.pack(pady=5)
    barra.set(0)
    barra.configure(progress_color="#1f6aa5")
    btn_iniciar_download.configure(state="disabled")
    
    def download_thread():
        try:
            def callback_progresso(p):
                # Atualizar barra de forma thread-safe
                janela.after(0, lambda: barra.set(p))
            
            titulo = baixar(campo_url.get(), campo_pasta.get(), formato.get(), 
                          callback_progresso, campo_nome_arquivo.get(), qualidade_var.get())
            salvar_download(titulo, formato.get(), campo_pasta.get())
            
            # Atualizar UI de forma thread-safe
            janela.after(0, lambda: _finalizar_download(titulo))
        except Exception as e:
            janela.after(0, lambda: _erro_download(str(e)))
    
    thread = threading.Thread(target=download_thread, daemon=True)
    thread.start()

def _finalizar_download(titulo):
    """Finaliza download e atualiza UI."""
    barra.set(1)
    barra.configure(progress_color="green")
    campo_url.delete(0, ctk.END)
    campo_nome_arquivo.delete(0, ctk.END)
    ler_historico()
    btn_iniciar_download.configure(state="normal")

def _erro_download(erro):
    """Mostra erro no download."""
    barra.configure(progress_color="red")
    label_titulo_video.configure(text=f"Erro no download: {erro}", text_color="red")
    btn_iniciar_download.configure(state="normal")

btn_iniciar_download = ctk.CTkButton(frame_down, text="Iniciar Download", command=iniciar_download)
btn_iniciar_download.pack(pady=5)

barra = ctk.CTkProgressBar(frame_down, width=400)
barra.set(0)

# ── ABA CONVERSOR 
label_conversor = ctk.CTkLabel(abas.tab("Conversor"), text="Arquivo escolhido: ")
label_conversor.pack(pady=5)

def escolher_arquivo():
    campo_arquivo.delete(0, ctk.END)
    campo_arquivo.insert(0, filedialog.askopenfilename())

campo_arquivo = ctk.CTkEntry(abas.tab("Conversor"), width=400)
campo_arquivo.pack(pady=5)

btn_arquivo = ctk.CTkButton(abas.tab("Conversor"), text="Escolher arquivo", command=escolher_arquivo)
btn_arquivo.pack(pady=5)

def abrir_pasta_conv():
    os.startfile(os.path.dirname(campo_arquivo.get()))

btn_abrir_pasta_conv = ctk.CTkButton(abas.tab("Conversor"), text="Abrir Pasta", command=abrir_pasta_conv)
btn_abrir_pasta_conv.pack(pady=5)

label_form = ctk.CTkLabel(abas.tab("Conversor"), text="Formato:")
label_form.pack(pady=5)

form = ctk.StringVar(value="1")

ctk.CTkRadioButton(abas.tab("Conversor"), text="MP4", variable=form, value="1").pack(pady=2)
ctk.CTkRadioButton(abas.tab("Conversor"), text="MP3", variable=form, value="2").pack(pady=2)
ctk.CTkRadioButton(abas.tab("Conversor"), text="WAV", variable=form, value="3").pack(pady=2)

label_status_conv = ctk.CTkLabel(abas.tab("Conversor"), text="")
label_status_conv.pack(pady=5)

def converter():
    caminho = campo_arquivo.get()
    form1 = form.get()
    form_original = os.path.splitext(caminho)[1]
    extensoes = {"1": ".mp4", "2": ".mp3", "3": ".wav"}
    if form_original == extensoes[form1]:
        label_status_conv.configure(text="Arquivo já está nesse formato!", text_color="red")
        return
    if form1 == "1":
        saida = os.path.splitext(caminho)[0] + ".mp4"
    elif form1 == "2":
        saida = os.path.splitext(caminho)[0] + ".mp3"
    elif form1 == "3":
        saida = os.path.splitext(caminho)[0] + ".wav"
    subprocess.run(["ffmpeg", "-i", caminho, saida])
    label_status_conv.configure(text="Conversão concluída!", text_color="green")
    campo_arquivo.delete(0, ctk.END)
    salvar_download(os.path.splitext(os.path.basename(caminho))[0], form1, os.path.dirname(caminho))
    ler_historico()

btn_converter = ctk.CTkButton(abas.tab("Conversor"), text="Converter", command=converter)
btn_converter.pack(pady=5)

# ── ABA HISTÓRICO 
label_historico = ctk.CTkLabel(abas.tab("Histórico"), text="Histórico de Downloads")
label_historico.pack(pady=5)

frame_historico = ctk.CTkScrollableFrame(abas.tab("Histórico"), width=450, height=400)
frame_historico.pack(pady=10)

btn_limpar = ctk.CTkButton(abas.tab("Histórico"), text="Limpar Histórico", command=apagar_historico, fg_color="red")
btn_limpar.pack(pady=5)

def ler_historico():
    """Carrega histórico de forma eficiente com atualização incremental."""
    for widget in frame_historico.winfo_children():
        widget.destroy()
    
    historico = carregar_historico()
    if not historico:
        ctk.CTkLabel(frame_historico, text="Nenhum download registrado", text_color="gray").pack()
        return
    
    # Exibe em ordem reversa (mais recentes primeiro)
    for item in reversed(historico):
        frame = ctk.CTkFrame(frame_historico, fg_color="#212121", border_color="#404040", border_width=1)
        frame.pack(pady=5, padx=5, fill="x")
        
        titulo_label = ctk.CTkLabel(
            frame, 
            text=item['titulo'], 
            font=("Arial", 11, "bold"),
            wraplength=400,
            justify="left"
        )
        titulo_label.pack(anchor="w", padx=10, pady=(5, 2))
        
        info_label = ctk.CTkLabel(
            frame,
            text=f"{item['data']} • {item['formato']}",
            font=("Arial", 9),
            text_color="gray",
            wraplength=400,
            justify="left"
        )
        info_label.pack(anchor="w", padx=10, pady=(2, 5))

ler_historico()

janela.mainloop()
