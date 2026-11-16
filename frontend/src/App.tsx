import { ChangeEvent, DragEvent, useCallback, useEffect, useRef, useState } from "react";
import {
  ArrowDownToLine, AudioLines, Check, ChevronDown, Clock3, FileArchive, FileAudio,
  FileImage, FileText, Film, FolderOpen, Gauge, History, Image as ImageIcon, LoaderCircle,
  MoreHorizontal, Pause, Play, Plus, Scissors, Settings2, ShieldCheck, Sparkles, Upload,
  X, Zap,
} from "lucide-react";

const API = "http://127.0.0.1:8000/api";
type Uploaded = { id: string; name: string; size: number; kind: string; formats: string[] };
type Job = { id: string; title: string; kind: string; status: string; progress: number; detail: string; error?: string; output?: string };
type Preset = { id: string; title: string; note: string; icon: typeof AudioLines; target: string };
const PRESETS: Preset[] = [
  { id: "audio", title: "Áudio alta qualidade", note: "WAV ou FLAC", icon: AudioLines, target: "flac" },
  { id: "compress", title: "Compactar mídia", note: "Alvo 16 MB", icon: Gauge, target: "mp4" },
  { id: "web", title: "Web otimizado", note: "WEBP leve", icon: Sparkles, target: "webp" },
  { id: "mp3", title: "Extrair MP3", note: "320 kbps", icon: FileAudio, target: "mp3" },
  { id: "pdf", title: "Juntar em PDF", note: "Documentos e imagens", icon: FileText, target: "pdf" },
];
const TERMINAL = ["completed", "failed", "cancelled"];

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API}${path}`, init);
  if (!response.ok) {
    let message = `Falha na solicitação (${response.status})`;
    try { message = (await response.json()).detail || message; } catch { /* resposta sem JSON */ }
    throw new Error(message);
  }
  return response.json() as Promise<T>;
}

function bytes(value: number) {
  if (!value) return "0 B";
  const unit = ["B", "KB", "MB", "GB"][Math.min(3, Math.floor(Math.log(value) / Math.log(1024)))];
  return `${(value / 1024 ** ["B", "KB", "MB", "GB"].indexOf(unit)).toFixed(1)} ${unit}`;
}

function FileGlyph({ kind }: { kind: string }) {
  if (kind === "image") return <FileImage />;
  if (kind === "media") return <Film />;
  if (kind === "document") return <FileText />;
  return <FileArchive />;
}

export default function App() {
  const [files, setFiles] = useState<Uploaded[]>([]);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [activeTab, setActiveTab] = useState("studio");
  const [url, setUrl] = useState("");
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [settings, setSettings] = useState({ output_folder: "", gpu: false, concurrency: 2, cleanup_days: 7 });
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const refreshJobs = useCallback(async () => {
    try {
      const result = await request<{ jobs: Job[] }>("/jobs");
      setJobs(result.jobs);
    } catch (error) { setNotice((error as Error).message); }
  }, []);

  useEffect(() => {
    refreshJobs();
    request<typeof settings>("/settings").then(setSettings).catch((error) => setNotice(error.message));
  }, [refreshJobs]);

  useEffect(() => {
    const active = jobs.filter((job) => !TERMINAL.includes(job.status));
    const sources = active.map((job) => {
      const source = new EventSource(`${API}/jobs/${job.id}/events`);
      source.onmessage = (event) => {
        const update = JSON.parse(event.data) as Partial<Job> & { job_id?: string };
        setJobs((previous) => previous.map((item) => item.id === job.id ? { ...item, ...update } : item));
        if (update.status && TERMINAL.includes(update.status)) source.close();
      };
      source.onerror = () => source.close();
      return source;
    });
    return () => sources.forEach((source) => source.close());
  }, [jobs.map((job) => `${job.id}:${job.status}`).join("|")]);

  const addFiles = async (incoming: FileList | File[]) => {
    if (!incoming.length) return;
    setBusy(true);
    setNotice("");
    try {
      const form = new FormData();
      Array.from(incoming).forEach((file) => form.append("files", file));
      const result = await request<{ files: Uploaded[] }>("/files", { method: "POST", body: form });
      setFiles((existing) => [...existing, ...result.files]);
      if (result.files.length < incoming.length) setNotice("Alguns arquivos não têm um formato suportado.");
    } catch (error) { setNotice((error as Error).message); }
    finally { setBusy(false); }
  };

  const onDrop = (event: DragEvent) => {
    event.preventDefault();
    setDragging(false);
    void addFiles(event.dataTransfer.files);
  };

  const submitFiles = async (targetOverride?: string) => {
    if (!files.length) { setNotice("Adicione arquivos primeiro."); return; }
    setBusy(true);
    setNotice("");
    try {
      const created = await Promise.all(files.map((file) => {
        const target = targetOverride && file.formats.includes(targetOverride)
          ? targetOverride : file.formats.includes(file.formats[0]) ? file.formats[0] : "";
        if (!target) return Promise.resolve(null);
        const options = target === "mp3" ? { bitrate: 320 } :
          target === "flac" || target === "wav" ? { normalize: false } :
          target === "webp" ? { quality: 82 } :
          target === "mp4" && activePreset.current === "compress" ? { compress_mb: 16 } : { gpu: settings.gpu };
        return request<Job>("/jobs/process", {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ file_id: file.id, target, options }),
        });
      }));
      setJobs((existing) => [...created.filter((job): job is Job => !!job), ...existing]);
      setFiles([]);
      setActiveTab("queue");
    } catch (error) { setNotice((error as Error).message); }
    finally { setBusy(false); }
  };

  const activePreset = useRef("");
  const applyPreset = (preset: Preset) => {
    activePreset.current = preset.id;
    setFiles((items) => items.map((file) => file.formats.includes(preset.target)
      ? file : { ...file, formats: [preset.target, ...file.formats] }));
    setNotice(`Preset “${preset.title}” selecionado. Ajuste os formatos na fila e inicie o processamento.`);
  };

  const addUrl = async (event?: ChangeEvent<HTMLFormElement>) => {
    event?.preventDefault();
    if (!url.trim()) { setNotice("Cole uma URL para iniciar o download."); return; }
    setBusy(true);
    setNotice("");
    try {
      const job = await request<Job>("/jobs/download", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url: url.trim(), options: { audio_format: "mp3", bitrate: 320, gpu: settings.gpu } }),
      });
      setJobs((previous) => [job, ...previous]);
      setUrl("");
      setActiveTab("queue");
    } catch (error) { setNotice((error as Error).message); }
    finally { setBusy(false); }
  };

  const paste = async () => {
    try {
      const text = await navigator.clipboard.readText();
      if (/^https?:\/\//i.test(text.trim())) setUrl(text.trim());
    } catch { setNotice("Acesso à área de transferência indisponível."); }
  };

  const saveSettings = async () => {
    try {
      const saved = await request<typeof settings>("/settings", {
        method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(settings),
      });
      setSettings(saved);
      setSettingsOpen(false);
      setNotice("Preferências salvas.");
    } catch (error) { setNotice((error as Error).message); }
  };

  const cancel = async (id: string) => {
    try { await request(`/jobs/${id}/cancel`, { method: "POST" }); }
    catch (error) { setNotice((error as Error).message); }
  };

  const downloadZip = () => { window.location.href = `${API}/outputs.zip`; };
  const activeJobs = jobs.filter((job) => !TERMINAL.includes(job.status)).length;

  return (
    <div className="shell" onDragOver={(event) => { event.preventDefault(); setDragging(true); }} onDragLeave={() => setDragging(false)} onDrop={onDrop}>
      <aside className="sidebar">
        <div className="brand"><div className="brand-mark"><Zap size={17} fill="currentColor" /></div><span>MEDIA<span className="brand-light">STUDIO</span></span></div>
        <div className="workspace-label">WORKSPACE</div>
        <nav>
          <button className={activeTab === "studio" ? "nav-item selected" : "nav-item"} onClick={() => setActiveTab("studio")}><Sparkles size={16} /> Studio <span className="nav-shortcut">⌘ 1</span></button>
          <button className={activeTab === "queue" ? "nav-item selected" : "nav-item"} onClick={() => setActiveTab("queue")}><ArrowDownToLine size={16} /> Fila {activeJobs > 0 && <span className="nav-count">{activeJobs}</span>}</button>
          <button className={activeTab === "history" ? "nav-item selected" : "nav-item"} onClick={() => setActiveTab("history")}><History size={16} /> Histórico</button>
        </nav>
        <div className="sidebar-bottom">
          <div className="engine-state"><span className="online-dot" /><span>Processamento local</span></div>
          <button className="nav-item" onClick={() => setSettingsOpen(true)}><Settings2 size={16} /> Configurações</button>
          <div className="user-badge"><div className="avatar">MS</div><div><strong>Media Studio</strong><small>Instância local</small></div><MoreHorizontal size={17} /></div>
        </div>
      </aside>

      <main className="main">
        <header className="topbar"><div className="breadcrumb">Studio <span>/</span> <b>{activeTab === "studio" ? "Novo projeto" : activeTab === "queue" ? "Fila de processamento" : "Histórico"}</b></div><div className="top-actions"><span className="secure-label"><ShieldCheck size={14} /> Seus arquivos ficam locais</span><button className="icon-btn" title="Configurações" onClick={() => setSettingsOpen(true)}><Settings2 size={17} /></button></div></header>
        <div className="content">
          {activeTab === "studio" && <>
            <section className="page-heading"><div><div className="eyebrow"><span className="eyebrow-line" /> UNIVERSAL CONVERTER</div><h1>O seu estúdio de arquivos.</h1><p>Baixe, transforme e otimize qualquer mídia em um só lugar.</p></div><span className="version-pill">BETA <span>·</span> 1.0</span></section>
            <section className={`dropzone ${dragging ? "drag-active" : ""}`} onClick={() => inputRef.current?.click()} onDragOver={(event) => { event.preventDefault(); setDragging(true); }} onDrop={onDrop}>
              <input ref={inputRef} type="file" multiple hidden onChange={(event) => { if (event.target.files) void addFiles(event.target.files); event.target.value = ""; }} />
              <div className="upload-symbol"><Upload size={19} /></div><div className="drop-copy"><strong>Solte arquivos para começar</strong><span>ou <button className="text-button" onClick={(event) => { event.stopPropagation(); inputRef.current?.click(); }}>escolha no computador</button> · múltiplos arquivos</span></div>
              <div className="drop-divider"><span>OU BAIXE DA WEB</span></div>
              <form className="url-entry" onSubmit={addUrl} onClick={(event) => event.stopPropagation()}><div className="url-icon"><ArrowDownToLine size={16} /></div><input value={url} onChange={(event) => setUrl(event.target.value)} placeholder="Cole uma URL do YouTube, TikTok, Instagram..." /><button className="paste-button" type="button" onClick={paste}>Colar</button><button className="url-submit" disabled={busy || !url.trim()} type="submit">{busy ? <LoaderCircle className="spin" size={16} /> : <ArrowDownToLine size={16} />}<span>Adicionar</span></button></form>
              <div className="supported-sites">Suporta YouTube <i /> Instagram <i /> TikTok <i /> X <i /> SoundCloud <i /> Twitch <i /> Reddit</div>
            </section>

            <div className="section-title"><div><h2>Comece com um preset</h2><p>Um clique para as tarefas mais comuns.</p></div><button className="subtle-button" onClick={() => setFiles([])}>Limpar seleção</button></div>
            <section className="presets">{PRESETS.map((preset) => { const Icon = preset.icon; return <button className="preset-card" key={preset.id} onClick={() => applyPreset(preset)}><span className="preset-icon"><Icon size={17} /></span><span className="preset-copy"><strong>{preset.title}</strong><small>{preset.note}</small></span><ChevronDown className="preset-arrow" size={14} /></button>; })}</section>

            <div className="section-title queue-title"><div><h2>Arquivos para converter <span className="count-pill">{files.length}</span></h2><p>Formatos detectados automaticamente e opções compatíveis.</p></div>{files.length > 0 && <button className="primary-button compact" onClick={() => void submitFiles()} disabled={busy}>{busy ? <LoaderCircle className="spin" size={15} /> : <Play size={14} />} Processar tudo</button>}</div>
            <section className="file-list">
              {files.length ? files.map((file) => <div className="file-row" key={file.id}><span className={`file-icon ${file.kind}`}><FileGlyph kind={file.kind} /></span><div className="file-info"><strong>{file.name}</strong><small>{bytes(file.size)} <span>·</span> {file.kind}</small></div><span className="arrow-label">PARA</span><select aria-label={`Formato de saída para ${file.name}`} defaultValue={file.formats[0]} onChange={(event) => setFiles((all) => all.map((item) => item.id === file.id ? { ...item, formats: [event.target.value, ...item.formats.filter((format) => format !== event.target.value)] } : item))}>{file.formats.map((format) => <option key={format} value={format}>{format.toUpperCase()}</option>)}</select><button className="remove-file" title="Remover" onClick={() => setFiles((all) => all.filter((item) => item.id !== file.id))}><X size={15} /></button></div>) : <div className="empty-files"><div className="empty-icon"><FileArchive size={19} /></div><div><strong>Sua fila está pronta</strong><span>Adicione arquivos ou cole uma URL acima para começar.</span></div><button className="subtle-button" onClick={() => inputRef.current?.click()}><Plus size={14} /> Adicionar arquivo</button></div>}
            </section>
            {notice && <div className="notice" role="status">{notice}<button onClick={() => setNotice("")}><X size={14} /></button></div>}
            <footer className="content-footer"><span><ShieldCheck size={14} /> Processado na sua máquina. Privado por design.</span><span>FFmpeg <i /> yt-dlp <i /> Pillow</span></footer>
          </>}

          {activeTab === "queue" && <><section className="page-heading"><div><div className="eyebrow"><span className="eyebrow-line" /> LIVE QUEUE</div><h1>Fila de processamento</h1><p>Acompanhe seus downloads e conversões em tempo real.</p></div><button className="secondary-button" onClick={downloadZip}><FileArchive size={15} /> Baixar tudo em ZIP</button></section>
            <JobList jobs={jobs} cancel={cancel} /><div className="queue-add"><button className="secondary-button" onClick={() => setActiveTab("studio")}><Plus size={15} /> Adicionar mais arquivos</button></div></>}

          {activeTab === "history" && <><section className="page-heading"><div><div className="eyebrow"><span className="eyebrow-line" /> RECENT ACTIVITY</div><h1>Histórico</h1><p>Seus trabalhos recentes, armazenados localmente.</p></div><button className="secondary-button" onClick={refreshJobs}><Clock3 size={15} /> Atualizar</button></section><JobList jobs={jobs.filter((job) => TERMINAL.includes(job.status))} cancel={cancel} history /></>}
        </div>
      </main>
      {settingsOpen && <div className="modal-backdrop" onMouseDown={(event) => { if (event.target === event.currentTarget) setSettingsOpen(false); }}><section className="settings-modal"><div className="modal-heading"><div><span className="eyebrow">PREFERÊNCIAS</span><h2>Configurações</h2></div><button className="icon-btn" onClick={() => setSettingsOpen(false)}><X size={17} /></button></div><label className="setting-field">Pasta de saída<input value={settings.output_folder} onChange={(event) => setSettings({ ...settings, output_folder: event.target.value })} placeholder="Deixe vazio para usar a pasta do Studio" /><small>O destino local é mantido entre sessões.</small></label><label className="setting-check"><span><strong>Aceleração por GPU</strong><small>Usar NVENC quando disponível no FFmpeg</small></span><input type="checkbox" checked={settings.gpu} onChange={(event) => setSettings({ ...settings, gpu: event.target.checked })} /></label><label className="setting-field">Tarefas simultâneas<select value={settings.concurrency} onChange={(event) => setSettings({ ...settings, concurrency: Number(event.target.value) })}><option value={1}>1 tarefa</option><option value={2}>2 tarefas</option><option value={4}>4 tarefas</option><option value={8}>8 tarefas</option></select></label><label className="setting-field">Limpeza de arquivos temporários<select value={settings.cleanup_days} onChange={(event) => setSettings({ ...settings, cleanup_days: Number(event.target.value) })}><option value={0}>Não limpar automaticamente</option><option value={1}>Após 1 dia</option><option value={7}>Após 7 dias</option><option value={30}>Após 30 dias</option></select></label><div className="modal-actions"><button className="secondary-button" onClick={() => setSettingsOpen(false)}>Cancelar</button><button className="primary-button compact" onClick={() => void saveSettings()}><Check size={15} /> Salvar preferências</button></div></section></div>}
    </div>
  );
}

function JobList({ jobs, cancel, history = false }: { jobs: Job[]; cancel: (id: string) => void; history?: boolean }) {
  if (!jobs.length) return <div className="empty-panel"><div className="empty-icon"><History size={20} /></div><strong>{history ? "Ainda não há histórico" : "Nenhuma tarefa na fila"}</strong><span>As tarefas iniciadas aparecem aqui.</span></div>;
  return <section className="job-list">{jobs.map((job) => <article className="job-card" key={job.id}><div className={`job-icon ${job.status}`}><FileGlyph kind={job.kind === "download" ? "media" : "document"} /></div><div className="job-main"><div className="job-title-row"><strong>{job.title}</strong><span className={`status-tag ${job.status}`}>{job.status === "completed" ? <Check size={12} /> : job.status === "running" ? <LoaderCircle size={12} className="spin" /> : null}{job.status === "completed" ? "Concluído" : job.status === "running" ? "Processando" : job.status === "queued" ? "Na fila" : job.status === "failed" ? "Falhou" : "Cancelado"}</span></div><div className="job-detail">{job.error || job.detail || (job.status === "queued" ? "Aguardando worker" : "")}</div><div className="progress-track"><span style={{ width: `${Math.round(job.progress * 100)}%` }} /></div><div className="job-meta"><span>{Math.round(job.progress * 100)}% concluído</span>{job.status === "running" && <span><LoaderCircle size={11} className="spin" /> Em andamento</span>}</div></div><div className="job-actions">{job.status === "completed" && <a className="icon-btn" title="Baixar arquivo" href={`${API}/jobs/${job.id}/output`}><ArrowDownToLine size={16} /></a>}{!history && !TERMINAL.includes(job.status) && <button className="icon-btn" title="Cancelar tarefa" onClick={() => cancel(job.id)}><Pause size={15} /></button>}<span className="job-menu"><MoreHorizontal size={17} /></span></div></article>)}</section>;
}
