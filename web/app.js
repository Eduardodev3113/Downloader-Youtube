// Pequeno barramento de eventos que o Python usa pra empurrar
// atualizações (ex.: progresso do download) pro JS.
window.__deck = {
  listeners: {},
  on(event, fn) {
    (this.listeners[event] = this.listeners[event] || []).push(fn);
  },
  once(event, fn) {
    const wrapper = (payload) => {
      fn(payload);
      // Remove o listener após uma execução
      this.listeners[event] = (this.listeners[event] || []).filter(f => f !== wrapper);
    };
    this.on(event, wrapper);
  },
  emit(event, payload) {
    (this.listeners[event] || []).forEach((fn) => fn(payload));
  },
};

const FORMATO_LABEL = { "1": "MP4", "2": "MP3", "3": "WAV" };

function api() {
  return window.pywebview.api;
}

function $(id) {
  return document.getElementById(id);
}

function setLed(state) {
  const led = $("statusLed");
  led.classList.remove("busy", "ok", "error");
  if (state) led.classList.add(state);
  if (state === "ok" || state === "error") {
    setTimeout(() => led.classList.remove(state), 1600);
  }
}

function setStatus(el, message, kind) {
  el.textContent = message || "";
  el.classList.remove("ok", "error", "busy");
  if (kind) el.classList.add(kind);
}

// ---------------- Tabs ----------------

function setupTabs() {
  const channels = document.querySelectorAll(".channel");
  channels.forEach((btn) => {
    btn.addEventListener("click", () => {
      channels.forEach((c) => c.classList.remove("active"));
      btn.classList.add("active");

      document.querySelectorAll(".view").forEach((v) => v.classList.remove("active"));
      $(`view-${btn.dataset.view}`).classList.add("active");

      if (btn.dataset.view === "historico") {
        loadHistorico();
      }
    });
  });
}

// ---------------- Downloader ----------------

function setupDownloader() {
  const inputUrl = $("inputUrl");
  const btnBuscar = $("btnBuscar");
  const preview = $("preview");
  const thumbImg = $("thumbImg");
  const previewTitulo = $("previewTitulo");
  const previewMeta = $("previewMeta");
  const selectQualidade = $("selectQualidade");
  const inputNome = $("inputNome");
  const inputPasta = $("inputPasta");
  const btnPasta = $("btnPasta");
  const btnAbrirPasta = $("btnAbrirPasta");
  const btnDownload = $("btnDownload");
  const meterBlock = $("meterBlock");
  const meterFill = $("meterFill");
  const meterReadout = $("meterReadout");
  const downloadStatus = $("downloadStatus");

  function formatarDuracao(segundos) {
    if (!segundos) return "";
    const m = Math.floor(segundos / 60);
    const s = Math.floor(segundos % 60)
      .toString()
      .padStart(2, "0");
    return `${m}:${s}`;
  }

  btnBuscar.addEventListener("click", async () => {
    const url = inputUrl.value.trim();
    if (!url) {
      setStatus(downloadStatus, "Cole uma URL antes de buscar.", "error");
      return;
    }
    setLed("busy");
    btnBuscar.disabled = true;
    setStatus(downloadStatus, "Buscando informações do vídeo...", "busy");

    // Aguarda o resultado via evento
    window.__deck.once("buscar_info_done", (info) => {
      btnBuscar.disabled = false;

      if (!info.ok) {
        setLed("error");
        setStatus(downloadStatus, `Não foi possível buscar o vídeo: ${info.erro}`, "error");
        preview.hidden = true;
        return;
      }

      setLed("ok");
      setStatus(downloadStatus, "", null);

      thumbImg.src = info.thumbnail || "";
      previewTitulo.textContent = info.titulo;
      const partes = [formatarDuracao(info.duracao), info.canal].filter(Boolean);
      previewMeta.textContent = partes.join(" · ");
      preview.hidden = false;

      selectQualidade.innerHTML = "";
      info.qualidades.forEach((q) => {
        const opt = document.createElement("option");
        opt.value = q;
        opt.textContent = q;
        selectQualidade.appendChild(opt);
      });
    });

    // Inicia busca (retorna imediatamente)
    api().buscar_info(url);
  });

  btnPasta.addEventListener("click", async () => {
    const pasta = await api().escolher_pasta();
    if (pasta) inputPasta.value = pasta;
  });

  btnAbrirPasta.addEventListener("click", async () => {
    if (!inputPasta.value) return;
    await api().abrir_pasta(inputPasta.value);
  });

  window.__deck.on("download_progress", ({ percentual }) => {
    const pct = Math.min(100, Math.round(percentual * 100));
    meterFill.style.width = pct + "%";
    meterReadout.textContent = pct + "%";
  });

  window.__deck.on("download_done", (result) => {
    btnDownload.disabled = false;
    if (result.ok) {
      setLed("ok");
      setStatus(downloadStatus, `Concluído: ${result.titulo}`, "ok");
      inputUrl.value = "";
      inputNome.value = "";
      preview.hidden = true;
    } else {
      setLed("error");
      setStatus(downloadStatus, `Erro no download: ${result.erro}`, "error");
    }
  });

  btnDownload.addEventListener("click", async () => {
    const url = inputUrl.value.trim();
    const pasta = inputPasta.value.trim();
    if (!url || !pasta) {
      setStatus(downloadStatus, "Informe a URL e escolha a pasta de destino.", "error");
      return;
    }
    const formato = document.querySelector('input[name="formato"]:checked').value;
    const nome = inputNome.value.trim();
    const qualidade = selectQualidade.value || "Melhor qualidade";

    btnDownload.disabled = true;
    meterBlock.hidden = false;
    meterFill.style.width = "0%";
    meterReadout.textContent = "0%";
    setLed("busy");
    setStatus(downloadStatus, "Baixando...", "busy");

    const res = await api().iniciar_download(url, pasta, formato, nome, qualidade);
    if (!res.ok) {
      btnDownload.disabled = false;
      setLed("error");
      setStatus(downloadStatus, res.erro, "error");
    }
  });
}

// ---------------- Conversor ----------------

function setupConversor() {
  const inputArquivo = $("inputArquivo");
  const btnArquivo = $("btnArquivo");
  const btnAbrirPastaConv = $("btnAbrirPastaConv");
  const btnConverter = $("btnConverter");
  const convStatus = $("convStatus");

  btnArquivo.addEventListener("click", async () => {
    const arquivo = await api().escolher_arquivo();
    if (arquivo) inputArquivo.value = arquivo;
  });

  btnAbrirPastaConv.addEventListener("click", async () => {
    if (!inputArquivo.value) return;
    await api().abrir_pasta(inputArquivo.value);
  });

  btnConverter.addEventListener("click", async () => {
    const caminho = inputArquivo.value.trim();
    if (!caminho) {
      setStatus(convStatus, "Escolha um arquivo antes de converter.", "error");
      return;
    }
    const formato = document.querySelector('input[name="formatoConv"]:checked').value;

    btnConverter.disabled = true;
    setLed("busy");
    setStatus(convStatus, "Convertendo...", "busy");

    // Aguarda o resultado via evento
    window.__deck.once("converter_done", (res) => {
      btnConverter.disabled = false;

      if (res.ok) {
        setLed("ok");
        setStatus(convStatus, "Conversão concluída.", "ok");
        inputArquivo.value = "";
      } else {
        setLed("error");
        setStatus(convStatus, res.erro, "error");
      }
    });

    // Inicia conversão (retorna imediatamente)
    api().converter(caminho, formato);
  });
}

// ---------------- Histórico ----------------

async function loadHistorico() {
  const list = $("historyList");
  const historico = await api().carregar_historico();

  if (!historico.length) {
    list.innerHTML = `<div class="history-empty">Nenhum download ainda. Assim que você baixar algo, aparece aqui.</div>`;
    return;
  }

  list.innerHTML = "";
  [...historico].reverse().forEach((item) => {
    const row = document.createElement("div");
    row.className = "history-item";
    row.innerHTML = `
      <span class="history-date">${item.data}</span>
      <span class="history-title" title="${item.titulo}">${item.titulo}</span>
      <span class="history-badge fmt-${item.formato}">${FORMATO_LABEL[item.formato] || item.formato}</span>
    `;
    list.appendChild(row);
  });
}

function setupHistorico() {
  $("btnLimpar").addEventListener("click", async () => {
    await api().limpar_historico();
    loadHistorico();
  });
}

// ---------------- Boot ----------------

function init() {
  setupTabs();
  setupDownloader();
  setupConversor();
  setupHistorico();
}

if (window.pywebview) {
  init();
} else {
  window.addEventListener("pywebviewready", init);
}
