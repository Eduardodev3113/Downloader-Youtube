# YouTube Downloader — Deck

Aplicação desktop para baixar vídeos do YouTube e converter arquivos de áudio/vídeo.

Backend 100% Python (yt-dlp + ffmpeg), interface em HTML/CSS/JS rodando dentro de
uma janela nativa via [`pywebview`](https://pywebview.flowrl.com/). Antes a interface
era CustomTkinter — como o CustomTkinter não suporta CSS, a UI foi movida pra web
(sem virar site: continua um app desktop de janela única, sem servidor, sem navegador
separado).

---

## Estrutura do projeto

```
├── app.py           # Janela pywebview + ponte Python <-> JS (substitui interface.py)
├── downloader.py     # Lógica de download (yt-dlp) — igual a antes, só trocou o callback de progresso
├── historico.py      # Histórico em JSON — sem nenhuma mudança
├── requirements.txt
└── web/
    ├── index.html     # Estrutura das 3 abas: Baixar / Converter / Histórico
    ├── style.css       # Tema "deck" (grafite + âmbar/teal, medidor segmentado)
    └── app.js          # Chama window.pywebview.api.* e escuta eventos de progresso
```

`downloader.py` e `historico.py` continuam puros — nenhuma linha de UI neles.
Toda a interação com a interface passa por `app.py`, que expõe uma classe `Api`
para o JavaScript chamar (`buscar_info`, `iniciar_download`, `converter`,
`escolher_pasta`, `carregar_historico`, etc).

---

## Funcionalidades

- Download de vídeos do YouTube em **MP4**, **MP3** e **WAV**
- Escolha da qualidade do vídeo (144p até 4K)
- Prévia da thumbnail, título, canal e duração antes de baixar
- Escolha da pasta de destino e nome do arquivo
- Medidor de progresso segmentado em tempo real
- **Conversor** de formatos (MP4, MP3, WAV) com validação de formato repetido
- **Histórico de downloads/conversões** com data, título e formato
- Interface escura, tema "console de transmissão"

---

## Requisitos

- Python 3.9+
- [ffmpeg](https://ffmpeg.org/) instalado e no PATH
- No Windows, o pywebview usa o WebView2 (já vem com Windows 10/11 atualizado)
- No Linux, precisa de `webkit2gtk`: `sudo apt install python3-gi gir1.2-webkit2-4.1` (ou similar, varia por distro)
- No macOS funciona nativamente via WKWebView

## Instalação

```bash
git clone https://github.com/Eduardodev3113/Downloader-Youtube.git
cd Downloader-Youtube
pip install -r requirements.txt
```

**ffmpeg:**

- Windows: `winget install ffmpeg`
- Mac: `brew install ffmpeg`
- Linux: `sudo apt install ffmpeg`

## Como usar

```bash
python app.py
```

## Gerando um executável (PyInstaller)

Como agora tem uma pasta `web/` com os assets da interface, ela precisa ser
incluída manualmente nos dados do bundle:

```bash
pyinstaller --noconfirm --windowed --name "YT-Deck" \
  --add-data "web:web" \
  --icon icone.ico \
  app.py
```

(No Windows, troque `:` por `;` no `--add-data`, ou seja `--add-data "web;web"`.)

---

## Tecnologias

| Tecnologia | Uso |
| --- | --- |
| yt-dlp | Download de vídeos |
| pywebview | Janela nativa renderizando a interface HTML/CSS/JS |
| ffmpeg | Conversão de formatos |
| threading | Download sem travar a interface |
| HTML/CSS/JS | Interface — substitui o CustomTkinter |
| json | Armazenamento do histórico |

## Universal Media & File Converter Studio

O projeto também inclui uma versão local/web modular em `backend/` e `frontend/`.
Ela não substitui nem modifica o app desktop existente.

### Arquitetura adicionada

```text
backend/
  main.py                 # API FastAPI, fila limitada, SSE, uploads e histórico SQLite
  config.py               # Diretórios e limites configuráveis
  services/
    downloader_service.py # yt-dlp com validação de domínio e URL
    media_service.py      # FFmpeg para áudio/vídeo
    image_service.py      # Pillow, CairoSVG e rembg opcional
    doc_service.py        # PyMuPDF, Pandoc e LibreOffice
    data_service.py       # Pandas para CSV/XLSX/JSON/XML/YAML/SQL
frontend/
  src/App.tsx             # Interface React, omni-dropzone, presets e fila SSE
  src/style.css           # Design system escuro responsivo
Dockerfile                # API com FFmpeg, Pandoc, LibreOffice e Tesseract
docker-compose.yml        # API e frontend local
```

### Rodar localmente

Instale Python 3.10+, Node.js 20+, FFmpeg, Pandoc, LibreOffice e Tesseract.
No Windows, execute `start.bat`; no macOS/Linux, execute `sh start.sh`.
Ou rode `docker compose up --build` e abra `http://127.0.0.1:5173`.

A API fica em `http://127.0.0.1:8000` e a documentação interativa em
`http://127.0.0.1:8000/docs`. Os uploads e resultados ficam em `backend/data/`
(ou no volume `studio-data` ao usar Docker). A fila e os metadados são locais.

Downloads de URL aceitam somente domínios de mídia explicitamente suportados e
recusam endereços IP privados/locais. Recursos como rembg e AVIF dependem dos
componentes adicionais disponíveis no ambiente; o erro do backend é reportado na tarefa.
