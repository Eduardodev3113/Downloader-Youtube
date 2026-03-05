import customtkinter as ctk
from tkinter import filedialog
from downloader import baixar
import threading
import os
import subprocess

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

janela = ctk.CTk()
janela.title("YouTube Downloader")
janela.geometry("500x550")

abas = ctk.CTkTabview(janela)
abas.pack(fill="both", expand=True)

abas.add("Downloader")
abas.add("Conversor")

# parte de baixar videos 
label_url = ctk.CTkLabel(abas.tab("Downloader"), text="URL do vídeo:")
label_url.pack(pady=5)

campo_url = ctk.CTkEntry(abas.tab("Downloader"), width=400)
campo_url.pack(pady=5)

label_nome_arquivo = ctk.CTkLabel(abas.tab("Downloader"), text="Nome do Arquivo:")
label_nome_arquivo.pack(pady=5)

campo_nome_arquivo = ctk.CTkEntry(abas.tab("Downloader"), width=400)
campo_nome_arquivo.pack(pady=5)

label_pasta = ctk.CTkLabel(abas.tab("Downloader"), text="Caminho para salvar:")
label_pasta.pack(pady=5)

def escolher_pasta():
    campo_pasta.delete(0, ctk.END)
    campo_pasta.insert(0, filedialog.askdirectory())

campo_pasta = ctk.CTkEntry(abas.tab("Downloader"), width=400)
campo_pasta.pack(pady=5)

btn_pasta = ctk.CTkButton(abas.tab("Downloader"), text="Escolher pasta", command=escolher_pasta)
btn_pasta.pack(pady=5)

label_formato = ctk.CTkLabel(abas.tab("Downloader"), text="Formato:")
label_formato.pack(pady=5)

formato = ctk.StringVar(value="1")

ctk.CTkRadioButton(abas.tab("Downloader"), text="MP4", variable=formato, value="1").pack(pady=2)
ctk.CTkRadioButton(abas.tab("Downloader"), text="MP3", variable=formato, value="2").pack(pady=2)
ctk.CTkRadioButton(abas.tab("Downloader"), text="WAV", variable=formato, value="3").pack(pady=2)

def abrir_pasta():
    os.startfile(campo_pasta.get())

btn_abrir_pasta = ctk.CTkButton(abas.tab("Downloader"), text="Abrir Pasta", command=abrir_pasta)
btn_abrir_pasta.pack(pady=5)

def iniciar_download():
    barra.pack(pady=5)
    barra.set(0)
    barra.configure(progress_color="#1f6aa5")
    def download_thread():
        baixar(campo_url.get(), campo_pasta.get(), formato.get(), barra, campo_nome_arquivo.get())
        barra.set(1)
        barra.configure(progress_color="green")
    thread = threading.Thread(target=download_thread)
    thread.start()

btn_iniciar_download = ctk.CTkButton(abas.tab("Downloader"), text="Iniciar Download", command=iniciar_download)
btn_iniciar_download.pack(pady=5)

barra = ctk.CTkProgressBar(abas.tab("Downloader"), width=400)
barra.set(0)

# parte de converter wav pra mp4

label_conversor = ctk.CTkLabel(abas.tab("Conversor"), text="Arquivo escolhido: ")
label_conversor.pack(pady=5)

def escolher_arquivo():
    campo_arquivo.delete(0, ctk.END)
    campo_arquivo.insert(0, filedialog.askopenfilename())

campo_arquivo = ctk.CTkEntry(abas.tab("Conversor"), width=400)
campo_arquivo.pack(pady=5)

btn_pasta = ctk.CTkButton(abas.tab("Conversor"), text="Escolher arquivo", command=escolher_arquivo)
btn_pasta.pack(pady=5)

def abrir_pasta():
    os.startfile(os.path.dirname(campo_arquivo.get()))

btn_abrir_pasta = ctk.CTkButton(abas.tab("Conversor"), text="Abrir Pasta", command=abrir_pasta)
btn_abrir_pasta.pack(pady=5)

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
        
        print(f"O formato original já é {form_original} ")
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

btn_converter = ctk.CTkButton(abas.tab("Conversor"), text="Converter", command=converter)
btn_converter.pack(pady=5)

janela.mainloop()