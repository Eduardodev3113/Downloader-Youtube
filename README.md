# YouTube Downloader

Aplicação desktop para baixar vídeos do YouTube e converter arquivos de áudio/vídeo, com interface gráfica moderna.

---

## Funcionalidades

- Download de vídeos do YouTube em **MP4**, **MP3** e **WAV**
- Escolha da pasta de destino e nome do arquivo
- **Conversor** de formatos (MP4, MP3, WAV)
- Validação para evitar conversão desnecessária (mesmo formato)
- Barra de progresso com confirmação visual em verde
- Alertas de erro em vermelho
- Interface com tema escuro

---

## Estrutura do Projeto

```
├── downloader.py   # Lógica de download (yt-dlp)
├── interface.py    # Interface gráfica (CustomTkinter)
└── README.md
```

---

## Requisitos

- Python 3.7+
- [yt-dlp](https://github.com/yt-dlp/yt-dlp)
- [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter)
- [ffmpeg](https://ffmpeg.org/)

---

## ⚡ Download Rápido

Não quer instalar nada? Baixe o executável direto na seção de [Releases](https://github.com/Eduardodev3113/Downloader-Youtube/releases) e rode sem precisar de Python instalado.

---

## Instalação

**1. Clone o repositório:**
```bash
git clone https://github.com/seu-usuario/Downloader-Youtube.git
cd Downloader-Youtube
```

**2. Instale as dependências Python:**
```bash
pip install yt-dlp customtkinter
```

**3. Instale o ffmpeg:**

- **Windows:**
```bash
winget install ffmpeg
```
- **Mac:**
```bash
brew install ffmpeg
```
- **Linux:**
```bash
sudo apt install ffmpeg
```

---

## Como usar

```bash
python interface.py
```

### Aba Downloader
1. Cole a URL do vídeo do YouTube
2. Digite um nome para o arquivo (opcional)
3. Escolha a pasta de destino
4. Selecione o formato (MP4, MP3 ou WAV)
5. Clique em **Iniciar Download**

### Aba Conversor
1. Clique em **Escolher arquivo** e selecione o arquivo
2. Selecione o formato de saída
3. Clique em **Converter**

---

## Tecnologias

| Tecnologia | Uso |
|---|---|
| yt-dlp | Download de vídeos |
| CustomTkinter | Interface gráfica |
| ffmpeg | Conversão de formatos |
| threading | Download sem travar a interface |
| subprocess | Chamada do ffmpeg pelo Python |