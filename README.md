# YouTube Downloader

Aplicação desktop para baixar vídeos do YouTube e converter arquivos de áudio/vídeo, com interface gráfica moderna.

---

## Funcionalidades

- Download de vídeos do YouTube em **MP4**, **MP3** e **WAV**
- Escolha da qualidade do vídeo (144p até 4K)
- Prévia da thumbnail e título do vídeo antes de baixar
- Escolha da pasta de destino e nome do arquivo
- Barra de progresso em tempo real
- **Conversor** de formatos (MP4, MP3, WAV)
- Validação para evitar conversão desnecessária (mesmo formato)
- **Histórico de downloads** com data, título e formato
- Alertas visuais de sucesso (verde) e erro (vermelho)
- Interface com tema escuro e três abas

---

## Estrutura do Projeto

```
├── downloader.py   # Lógica de download (yt-dlp)
├── interface.py    # Interface gráfica (CustomTkinter)
├── historico.py    # Gerenciamento do histórico (JSON)
└── README.md
```

---

## Requisitos

- Python 3.7+
- [yt-dlp](https://github.com/yt-dlp/yt-dlp)
- [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter)
- [ffmpeg](https://ffmpeg.org/)
- [Pillow](https://python-pillow.org/)
- [requests](https://requests.readthedocs.io/)

---

## Download Rápido

Não quer instalar nada? Baixe o executável direto na seção de [Releases](https://github.com/Eduardodev3113/Downloader-Youtube/releases) e rode sem precisar de Python instalado.

---

## Instalação

**1. Clone o repositório:**
```bash
git clone https://github.com/Eduardodev3113/Downloader-Youtube.git
cd Downloader-Youtube
```

**2. Instale as dependências Python:**
```bash
pip install yt-dlp customtkinter Pillow requests
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
2. Clique em **Buscar** para ver a thumbnail, título e qualidades disponíveis
3. Escolha a qualidade desejada
4. Digite um nome para o arquivo (opcional)
5. Escolha a pasta de destino
6. Selecione o formato (MP4, MP3 ou WAV)
7. Clique em **Iniciar Download**

### Aba Conversor
1. Clique em **Escolher arquivo** e selecione o arquivo
2. Selecione o formato de saída
3. Clique em **Converter**

### Aba Histórico
- Mostra todos os downloads e conversões realizados
- Exibe título, formato e data de cada item
- Botão **Limpar Histórico** para apagar todos os registros

---

## Tecnologias

| Tecnologia | Uso |
|---|---|
| yt-dlp | Download de vídeos |
| CustomTkinter | Interface gráfica |
| ffmpeg | Conversão de formatos |
| threading | Download sem travar a interface |
| subprocess | Chamada do ffmpeg pelo Python |
| Pillow | Exibição da thumbnail na interface |
| requests | Download da thumbnail |
| json | Armazenamento do histórico |
