import { useEffect, useMemo, useState } from 'react';
import {
  ArrowLeft, ArrowRight, Check, CheckCircle2, CircleAlert,
  ClipboardCheck, Clock3, Download, FileSearch, FileText, FolderOpen,
  Layers3, Plus, RefreshCw, Search, ShieldCheck, UploadCloud,
  X,
} from 'lucide-react';

type Opportunity = { id: string; title: string; created_at: string };
type Document = { id: string; filename: string; page_count: number; sha256: string; needs_ocr_pages: number; ocr_pages: number };
type Citation = { document_id: string; page: number; quote: string };
type Claim = {
  id: string; kind: string; value: string; status: string; mandatory: boolean;
  citations: Citation[]; review_status: string | null; review_value: string | null;
  review_reason: string | null;
};
type Event = { stage: string; attempt: number; error_summary: string; occurred_at: string };
type Run = {
  id: string; status: string; error: string | null; created_at: string;
  brief: { title: string; claims: Claim[]; open_questions: string[] } | null;
  events: Event[]; progress: { done: number; total: number };
};
type OpportunityDetail = Opportunity & { documents: Document[]; latest_run: Run | null };

async function api<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, init);
  if (!response.ok) {
    const detail = await response.json().catch(() => ({}));
    throw new Error(detail.detail || `Request failed (${response.status})`);
  }
  return response.json() as Promise<T>;
}

const label: Record<string, string> = {
  buyer: 'Buyer', procurement_id: 'Reference ID', deadline: 'Submission deadline',
  scope: 'Scope of work', eligibility: 'Eligibility', required_document: 'Required document',
  technical_requirement: 'Technical requirement', evaluation_criterion: 'Evaluation criteria',
  disqualifier: 'Disqualifier', financial_term: 'Financial terms',
};

function formatDate(value: string) {
  return new Date(value).toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' });
}

function App() {
  const [opportunities, setOpportunities] = useState<Opportunity[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<OpportunityDetail | null>(null);
  const [selectedClaim, setSelectedClaim] = useState(0);
  const [search, setSearch] = useState('');
  const [newTitle, setNewTitle] = useState('');
  const [showCreate, setShowCreate] = useState(false);
  const [activeTab, setActiveTab] = useState<'brief' | 'activity'>('brief');
  const [mobilePane, setMobilePane] = useState<'detail' | 'source'>('detail');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [editValue, setEditValue] = useState('');
  const [reviewReason, setReviewReason] = useState('');

  const refreshList = async () => {
    try { setOpportunities(await api<Opportunity[]>('/v1/opportunities')); }
    catch (e) { setError((e as Error).message); }
  };
  const refreshDetail = async (id: string) => {
    try { setDetail(await api<OpportunityDetail>(`/v1/opportunities/${id}`)); }
    catch (e) { setError((e as Error).message); }
  };

  useEffect(() => { void refreshList(); }, []);
  useEffect(() => {
    if (!selectedId) return;
    void refreshDetail(selectedId);
    const timer = setInterval(() => void refreshDetail(selectedId), 4000);
    return () => clearInterval(timer);
  }, [selectedId]);

  const filtered = useMemo(() => opportunities.filter(o => o.title.toLowerCase().includes(search.toLowerCase())), [opportunities, search]);
  const run = detail?.latest_run;
  const claims = run?.brief?.claims || [];
  const claim = claims[Math.min(selectedClaim, Math.max(0, claims.length - 1))];
  const citation = claim?.citations[0];
  const reviewedCount = claims.filter(c => c.review_status === 'accepted' || c.review_status === 'edited').length;
  const completeDraft = run?.status === 'draft';

  async function createOpportunity(event: React.FormEvent) {
    event.preventDefault(); setError(''); setBusy(true);
    try {
      const item = await api<Opportunity>('/v1/opportunities', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ title: newTitle }) });
      await refreshList(); setSelectedId(item.id); setShowCreate(false); setNewTitle('');
    } catch (e) { setError((e as Error).message); } finally { setBusy(false); }
  }

  async function uploadDocument(file: File) {
    if (!selectedId) return;
    setError(''); setNotice(''); setBusy(true);
    try {
      const body = new FormData(); body.append('file', file);
      await api(`/v1/opportunities/${selectedId}/documents`, { method: 'POST', body });
      await refreshDetail(selectedId); setNotice('Document uploaded. Start extraction when the pack is complete.');
    } catch (e) { setError((e as Error).message); } finally { setBusy(false); }
  }

  async function startRun() {
    if (!selectedId) return;
    setError(''); setBusy(true);
    try {
      await api(`/v1/opportunities/${selectedId}/runs`, { method: 'POST' });
      await refreshDetail(selectedId); setNotice('Extraction queued. The worker will process this document pack.');
    } catch (e) { setError((e as Error).message); } finally { setBusy(false); }
  }

  async function retryRun() {
    if (!run || !selectedId) return;
    setError(''); setBusy(true);
    try {
      await api(`/v1/runs/${run.id}/retry`, { method: 'POST' });
      await refreshDetail(selectedId); setNotice('Incomplete extraction requeued from its saved checkpoints.');
    } catch (e) { setError((e as Error).message); } finally { setBusy(false); }
  }

  async function review(status: 'accepted' | 'edited' | 'unresolved') {
    if (!selectedId || !claim) return;
    const reason = status === 'accepted' ? 'Verified against cited source' : reviewReason.trim();
    if (!reason) return;
    setBusy(true); setError('');
    try {
      await api(`/v1/claims/${claim.id}/review`, {
        method: 'PATCH', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status, value: status === 'edited' ? editValue : null, reason }),
      });
      await refreshDetail(selectedId); setReviewReason(''); setEditValue('');
      if (selectedClaim < claims.length - 1) setSelectedClaim(selectedClaim + 1);
    } catch (e) { setError((e as Error).message); } finally { setBusy(false); }
  }

  async function exportBrief() {
    if (!run) return;
    setBusy(true); setError('');
    try {
      const exported = await api<object>(`/v1/runs/${run.id}/exports`, { method: 'POST' });
      const blob = new Blob([JSON.stringify(exported, null, 2)], { type: 'application/json' });
      const anchor = document.createElement('a'); anchor.href = URL.createObjectURL(blob);
      anchor.download = `tenderlens-${run.id}.json`; anchor.click(); URL.revokeObjectURL(anchor.href);
      setNotice('Approved brief exported.');
    } catch (e) { setError((e as Error).message); } finally { setBusy(false); }
  }

  return <div className="app-shell">
    <aside className="sidebar">
      <div className="brand"><div className="brand-mark"><Layers3 size={22} strokeWidth={2.2} /></div><div><strong>TenderLens</strong><small>INTELLIGENCE WORKSPACE</small></div></div>
      <div className="sidebar-section-title">WORKSPACE</div>
      <button className={`nav-item ${!selectedId ? 'active' : ''}`} onClick={() => { setSelectedId(null); setDetail(null); }}><FolderOpen size={17} /> Opportunities <span>{opportunities.length}</span></button>
      <button className="nav-item" onClick={() => setShowCreate(true)}><Plus size={17} /> New opportunity</button>
      <div className="sidebar-spacer" />
      <div className="sidebar-footer"><ShieldCheck size={18} /><div><strong>Source-first review</strong><small>Every claim linked to evidence</small></div></div>
    </aside>

    <main className="main-area">
      <header className="topbar"><div className="breadcrumbs"><span>Workspace</span><span className="crumb-divider">/</span><strong>{detail ? detail.title : 'Opportunities'}</strong></div><div className="topbar-right"><span className="environment-dot" /> Local service <div className="avatar">TL</div></div></header>
      {error && <div className="toast error" role="alert"><CircleAlert size={17} />{error}<button onClick={() => setError('')} aria-label="Dismiss error"><X size={16}/></button></div>}
      {notice && <div className="toast success" role="status"><CheckCircle2 size={17} />{notice}<button onClick={() => setNotice('')} aria-label="Dismiss notice"><X size={16}/></button></div>}

      {!detail ? <div className="page-content">
        <div className="eyebrow">PROCUREMENT INTELLIGENCE</div>
        <div className="page-head"><div><h1>Your opportunities<span className="headline-period">.</span></h1><p>Turn dense tender packs into clear, evidence-backed decisions.</p></div><button className="primary-button" onClick={() => setShowCreate(true)}><Plus size={18}/> New opportunity</button></div>
        <div className="metric-grid"><div className="metric-card"><div className="metric-icon navy"><FolderOpen size={19}/></div><span>Total opportunities</span><strong>{opportunities.length}</strong></div><div className="metric-card"><div className="metric-icon amber"><Clock3 size={19}/></div><span>Ready for analysis</span><strong>{opportunities.length}</strong></div><div className="metric-card"><div className="metric-icon green"><ClipboardCheck size={19}/></div><span>Evidence workflow</span><strong>On</strong></div></div>
        <section className="list-card"><div className="list-header"><div><h2>Opportunity pipeline</h2><p>Review documents and follow extraction progress</p></div><div className="search-box"><Search size={17}/><input aria-label="Search opportunities" placeholder="Search opportunities" value={search} onChange={e => setSearch(e.target.value)}/></div></div>
          {filtered.length ? <div className="opportunity-list">{filtered.map(item => <button className="opportunity-row" key={item.id} onClick={() => { setSelectedId(item.id); setSelectedClaim(0); }}><div className="row-file-icon"><FileText size={21}/></div><div className="row-main"><strong>{item.title}</strong><span>Created {formatDate(item.created_at)}</span></div><span className="pill neutral">Open workspace</span><ArrowRight size={18} className="row-arrow" /></button>)}</div>
          : <div className="empty-list"><div className="empty-illustration"><FileSearch size={34}/></div><h3>{search ? 'No matching opportunities' : 'Your pipeline starts here'}</h3><p>{search ? 'Try a different search term.' : 'Create an opportunity, add tender PDFs, and turn them into a reviewable brief.'}</p>{!search && <button className="secondary-button" onClick={() => setShowCreate(true)}>Create first opportunity</button>}</div>}
        </section>
      </div> : <div className="workspace-content">
        <div className="workspace-head"><div><button className="back-link" onClick={() => { setSelectedId(null); setDetail(null); }}><ArrowLeft size={15}/> All opportunities</button><div className="eyebrow">OPPORTUNITY WORKSPACE</div><h1>{detail.title}<span className="headline-period">.</span></h1><p>{detail.documents.length} document{detail.documents.length !== 1 ? 's' : ''} · Created {formatDate(detail.created_at)}</p></div><div className="workspace-actions"><label className="secondary-button upload-button"><UploadCloud size={17}/> Add PDF<input type="file" accept="application/pdf" disabled={busy} onChange={e => { if (e.target.files?.[0]) void uploadDocument(e.target.files[0]); e.target.value = ''; }}/></label>{(run?.status === 'partial' || run?.status === 'failed') && <button className="secondary-button" disabled={busy} onClick={retryRun}><RefreshCw size={17}/> Retry incomplete run</button>}<button className="primary-button" disabled={busy || !detail.documents.length} onClick={startRun}><RefreshCw size={17}/> Run extraction</button></div></div>
        <div className="document-strip"><span className="strip-label">SOURCE PACK</span>{detail.documents.length ? detail.documents.map(doc => <span className="document-chip" key={doc.id}><FileText size={15}/>{doc.filename}<small>{doc.page_count}p</small>{doc.needs_ocr_pages > 0 && <small className="ocr-warning">{doc.needs_ocr_pages} pages need OCR</small>}{doc.ocr_pages > 0 && <small>{doc.ocr_pages} OCR pages</small>}</span>) : <span className="strip-empty">Add a tender PDF to begin</span>}</div>
        <div className="workspace-tabs"><button className={activeTab === 'brief' ? 'tab active' : 'tab'} onClick={() => setActiveTab('brief')}>Review brief</button><button className={activeTab === 'activity' ? 'tab active' : 'tab'} onClick={() => setActiveTab('activity')}>Run history {run?.events?.length ? <span>{run.events.length}</span> : null}</button><div className="tab-spacer"/>{run && run.progress.total > 0 && <span className="review-progress">{run.progress.done} of {run.progress.total} chunks complete</span>}{completeDraft && <span className="review-progress">{reviewedCount} of {claims.length} reviewed</span>}</div>
        {activeTab === 'activity' ? <div className="activity-panel"><h2>Extraction activity</h2><p>Validation and operational events for this document pack.</p>{run ? <><div className="run-status"><span className={`status-dot ${run.status}`}/><strong>Run {run.status}</strong><code>{run.id}</code></div>{run.error && <div className="activity-error">{run.error}</div>}{run.events.length ? run.events.map((event, index) => <div className="event-row" key={index}><div className="event-icon"><CircleAlert size={16}/></div><div><strong>{event.stage.replaceAll('_', ' ')} · attempt {event.attempt}</strong><p>{event.error_summary}</p><small>{formatDate(event.occurred_at)}</small></div></div>) : <div className="quiet-state">No validation failures recorded for this run.</div>}</> : <div className="quiet-state">Start an extraction to see run history.</div>}</div>
        : run?.brief && (run.status === 'draft' || claims.length > 0) ? <>{!completeDraft && <div className="activity-error" role="status">Partial extraction: {run.progress.done} of {run.progress.total} chunks complete. These claims are for inspection only; review and export remain locked until the run finishes. {run.error || ''}</div>}<div className="workbench-mobile-switch"><button className={mobilePane === 'detail' ? 'active' : ''} onClick={() => setMobilePane('detail')}>Brief</button><button className={mobilePane === 'source' ? 'active' : ''} onClick={() => setMobilePane('source')}>Source PDF</button></div><div className="workbench">
          <div className="claim-nav"><div className="pane-title"><div><span className="overline">EXTRACTED INTELLIGENCE</span><h2>Bid brief</h2></div><span className="count-badge">{claims.length}</span></div><div className="claim-list">{claims.map((item, index) => <button key={item.id} className={`claim-item ${selectedClaim === index ? 'selected' : ''}`} onClick={() => { setSelectedClaim(index); setEditValue(''); setReviewReason(''); }}><span className="claim-type">{label[item.kind] || item.kind}</span><strong>{item.review_value || item.value}</strong><span className={`claim-state ${item.review_status || 'pending'}`}>{item.review_status === 'accepted' || item.review_status === 'edited' ? <Check size={12}/> : <CircleAlert size={12}/>} {item.review_status || 'Needs review'}</span></button>)}</div></div>
          <div className={`claim-detail ${mobilePane === 'source' ? 'mobile-hidden' : ''}`}>{claim ? <><div className="detail-topline"><span className="overline">CLAIM {selectedClaim + 1} OF {claims.length}</span><span className={`state-badge ${claim.review_status || 'pending'}`}>{claim.review_status || 'Needs review'}</span></div><h2>{label[claim.kind] || claim.kind}</h2><p className="claim-value">{claim.review_value || claim.value}</p>{claim.mandatory && <span className="mandatory-tag">Mandatory condition</span>}<div className="detail-divider"/><div className="evidence-title"><ShieldCheck size={17}/> Source evidence</div>{citation ? <div className="quote-card"><p>“{citation.quote}”</p><button onClick={() => setMobilePane('source')}><FileText size={15}/> Page {citation.page} <ArrowRight size={15}/></button></div> : <div className="missing-evidence"><CircleAlert size={18}/> No source citation. This claim needs manual verification.</div>}{completeDraft && <div className="decision-area"><h3>Review decision</h3><p>Check the source before accepting. Your decision is preserved in the export.</p><textarea aria-label="Corrected claim value" placeholder="Enter a corrected value if needed" value={editValue} onChange={e => setEditValue(e.target.value)}/><input className="review-reason" aria-label="Review reason" placeholder="Reason for correction or uncertainty" value={reviewReason} onChange={e => setReviewReason(e.target.value)}/><div className="decision-actions"><button className="accept-button" disabled={busy || !citation} onClick={() => review('accepted')}><Check size={16}/> Accept claim</button><button className="outline-button" disabled={busy || !editValue.trim() || !reviewReason.trim()} onClick={() => review('edited')}>Save correction</button><button className="text-button" disabled={busy || !reviewReason.trim()} onClick={() => review('unresolved')}>Mark unsure</button></div></div>}</> : <div className="quiet-state">No claims extracted from this pack.</div>}</div>
          <div className={`source-pane ${mobilePane === 'detail' ? 'mobile-hidden' : ''}`}><div className="source-pane-head"><div><span className="overline">SOURCE DOCUMENT</span><h2>{detail.documents.find(d => d.id === citation?.document_id)?.filename || 'Tender PDF'}</h2></div>{citation && <span className="page-badge">Page {citation.page}</span>}</div>{citation ? <><div className="source-quote"><span>LOCATE IN PAGE</span><p>{citation.quote}</p></div><iframe title="Source tender PDF" src={`/v1/documents/${citation.document_id}/file#page=${citation.page}&toolbar=0`} /></> : <div className="source-empty"><FileSearch size={32}/><p>Select a cited claim to inspect the PDF.</p></div>}</div>
        </div><div className="review-footer"><div><strong>{completeDraft ? 'Review before export' : 'Incomplete extraction'}</strong><span>{completeDraft ? `${reviewedCount} of ${claims.length} claims approved` : 'Finish the run before reviewing or exporting'}</span></div><button className="primary-button" disabled={!completeDraft || busy || !claims.length || reviewedCount !== claims.length} onClick={exportBrief}><Download size={17}/> Export approved brief</button></div></>
        : <div className="run-empty"><div className="run-empty-icon">{run?.status === 'failed' ? <CircleAlert size={32}/> : <FileSearch size={32}/>}</div><h2>{run?.status === 'queued' || run?.status === 'running' ? 'Extraction in progress' : run?.status === 'failed' ? 'Extraction needs attention' : 'Ready for analysis'}</h2><p>{run?.status === 'failed' ? run.error : run ? 'The worker is preparing a reviewable brief. This page updates automatically.' : 'Upload a tender pack and run extraction to generate a cited bid brief.'}</p>{run?.status === 'failed' && <button className="secondary-button" onClick={() => setActiveTab('activity')}>View run history</button>}</div>}
      </div>}
    </main>

    {showCreate && <div className="modal-backdrop" onClick={() => setShowCreate(false)}><form className="modal" onClick={e => e.stopPropagation()} onSubmit={createOpportunity}><div className="modal-icon"><Plus size={21}/></div><button className="modal-close" type="button" onClick={() => setShowCreate(false)} aria-label="Close"><X size={20}/></button><h2>New opportunity</h2><p>Give this tender a name. You can add source documents next.</p><label htmlFor="opportunity-title">Opportunity name</label><input id="opportunity-title" autoFocus required minLength={2} maxLength={200} placeholder="e.g. City infrastructure RFP" value={newTitle} onChange={e => setNewTitle(e.target.value)}/><div className="modal-actions"><button type="button" className="text-button" onClick={() => setShowCreate(false)}>Cancel</button><button type="submit" className="primary-button" disabled={busy}>Create opportunity <ArrowRight size={16}/></button></div></form></div>}
  </div>;
}

export default App;
