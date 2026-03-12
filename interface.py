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
    url = campo_url.get()
    with yt_dlp.YoutubeDL({}) as ydl:
        info = ydl.extract_info(url, download=False)
        thumb_url = info["thumbnail"]
        titulo = info["title"]
    img_data = requests.get(thumb_url).content
    img = Image.open(BytesIO(img_data)).resize((320, 180))
    ctk_img = CTkImage(img, size=(320, 180))
    label_thumb.configure(image=ctk_img, text="")
    label_thumb.image = ctk_img
    label_titulo_video.configure(text=titulo)
    qualidades = []
    for f in info["formats"]:
        if f.get("height"):
            qualidade = f"{f['height']}p"
            if qualidade not in qualidades:
                qualidades.append(qualidade)
    qualidades.sort(key=lambda x: int(x.replace("p", "")), reverse=True)
    menu_qualidade.configure(values=qualidades)
    qualidade_var.set(qualidades[0])

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
    def download_thread():
        titulo = baixar(campo_url.get(), campo_pasta.get(), formato.get(), barra, campo_nome_arquivo.get(), qualidade_var.get())
        salvar_download(titulo, formato.get(), campo_pasta.get())
        ler_historico()
        barra.set(1)
        barra.configure(progress_color="green")
        campo_url.delete(0, ctk.END)
        campo_nome_arquivo.delete(0, ctk.END)
    thread = threading.Thread(target=download_thread)
    thread.start()

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
    for widget in frame_historico.winfo_children():
        widget.destroy()
    for item in carregar_historico():
        ctk.CTkLabel(frame_historico, text=f"{item['data']} - {item['titulo']} - {item['formato']}", wraplength=420).pack()

ler_historico()

janela.mainloop()
