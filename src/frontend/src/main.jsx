import React, {useEffect, useRef, useState} from 'react';
import {createRoot} from 'react-dom/client';
import './style.css';
import PairedDemo from './PairedDemo.jsx';

const clock = ms => `${Math.floor(ms/60000).toString().padStart(2,'0')}:${Math.floor(ms/1000)%60 < 10?'0':''}${Math.floor(ms/1000)%60}`;
const label = s => (s || '').replaceAll('_',' ');

function App() {
  const query = new URLSearchParams(window.location.search);
  const [scenarios,setScenarios] = useState([]), [sid,setSid] = useState(['S001','S002','S003','S004','S006'].includes(query.get('scenario'))?query.get('scenario'):'S006');
  const [audience,setAudience] = useState('analyst'), [analysis,setAnalysis] = useState(null);
  const [caseId,setCaseId] = useState(query.get('case')), [error,setError] = useState(''), [busy,setBusy] = useState(false);
  const [cached,setCached] = useState(!!query.get('case')), [time,setTime] = useState(0), [selected,setSelected] = useState(null);
  const [mode,setMode] = useState('multi'), [ack,setAck] = useState(false), [token,setToken] = useState('');
  const [health,setHealth] = useState(null);
  const [featured,setFeatured] = useState([]), [allowance,setAllowance] = useState(null);
  const [workspace,setWorkspace] = useState(query.get('view')==='paired'?'paired':'replay');
  const video = useRef(null), comparison = useRef(null), reference = useRef(null), generation = useRef(0), initialized = useRef(false);
  const headers = {'Content-Type':'application/json', ...(token? {'X-Analysis-Code':token}:{})};
  const scenario = scenarios.find(s=>s.id===sid);
  const gaitPair = sid==='S004'||sid==='S006';
  const comparisonId = sid==='S006'?'S004':'S006';
  const comparisonScenario = scenarios.find(s=>s.id===comparisonId);
  const active = busy || ['queued','running'].includes(analysis?.state);
  async function api(path, options={}) {
    const r = await fetch(path,{...options,headers:{...headers,...options.headers}});
    if (!r.ok) { const data = await r.json().catch(()=>({})); throw new Error(data.detail || `Request failed (${r.status})`); }
    return r.json();
  }
  useEffect(()=>{
    Promise.all([api('/api/scenarios'),api('/api/health'),api('/api/demo/featured')]).then(([s,h,f])=>{
      setScenarios(s);setHealth(h);setFeatured(f);
      if(!query.get('case')) {const saved=f.find(c=>c.scenario_id===sid);if(saved) {setCaseId(saved.id);setCached(true);}}
    }).catch(e=>setError(e.message));
  },[]);
  useEffect(()=>{
    const rev = ++generation.current;
    setAnalysis(null);setSelected(null);
    if (!caseId) return;
    let timer;
    async function poll() {
      try {
        const value = await api(`/api/analyses/${caseId}?audience=${audience}`);
        if (generation.current!==rev) return;
        if (value.scenario_id!==sid) throw new Error('Analysis belongs to another replay.');
        setAnalysis(value);
        if(token&&allowance&&!['queued','running'].includes(value.state))setAllowance(await api('/api/access'));
        if (['queued','running'].includes(value.state)) timer = setTimeout(poll,1200);
      } catch(e) {if (generation.current===rev) setError(e.message);}
    }
    poll();return ()=>{generation.current++;clearTimeout(timer);};
  },[caseId,audience,token]);
  useEffect(()=>{
    if(!initialized.current) {initialized.current=true;return;}
    const saved=mode==='multi'?featured.find(c=>c.scenario_id===sid):null;
    setTime(0);setCaseId(saved?.id || null);setCached(!!saved);setAnalysis(null);setSelected(null);setAck(false);setError('');
    window.history.replaceState({},'',`?scenario=${sid}${saved?'&case='+saved.id:''}`);
  },[sid,mode]);
  async function analyze() {
    setError('');setBusy(true);setAck(false);
    try {
      const result = await api('/api/analyses',{method:'POST',body:JSON.stringify({scenario_id:sid,player_id:'P001',mode,client_request_id:crypto.randomUUID()})});
      setCached(result.cache_hit);setCaseId(result.case_id);
      if(result.allowance)setAllowance(result.allowance);
      window.history.replaceState({},'',`?scenario=${sid}&case=${result.case_id}`);
      if (caseId===result.case_id) setAnalysis(await api(`${result.url}?audience=${audience}`));
    } catch(e) {setError(e.message);} finally {setBusy(false);}
  }
  async function playPair() {
    setError('');
    const players = [video.current,comparison.current].filter(Boolean);
    players.forEach(v=>{v.pause();v.currentTime=5;});
    try {await Promise.all(players.map(v=>v.play()));}
    catch {players.forEach(v=>v.pause());setError('Playback unavailable. Check that both replay assets are present.');}
  }
  function evidenceClick(id) {
    const e = analysis?.evidence[id];if (!e) return;
    setSelected(e);
    comparison.current?.pause();
    if (e.kind==='frame') {
      const target = e.clip_id==='R001'?reference.current:video.current;
      if(target) {target.currentTime=e.clip_time_ms/1000;target.pause();}
    }
  }
  function citations(ids=[]) {return <div className="citations">{ids.map(id=><button key={id} onClick={()=>evidenceClick(id)}>{id.replace('daily:P001:','')}</button>)}</div>;}
  const narrative = analysis?.narratives?.[audience];
  const calls = analysis?.calls || [];
  const metrics = analysis?.history?.metrics || [];
  const metric = name=>metrics.find(m=>m.name===name)?.value;
  const historyCall = calls.find(c=>c.role==='history');
  const historyError = analysis?.branch_errors?.history;
  const historyStatus = historyError?'Failed':analysis?.history_output?(historyCall?.cache_hit?'Completed · cached':'Completed'):
    analysis?.mode==='single'&&analysis?.history?'Combined analyst':active?'Pending':'Not run';
  const acceptedHistory = (analysis?.decision?.accepted_evidence_ids || []).filter(id=>analysis?.evidence[id]?.kind==='history');
  const priorInjuries = (analysis?.history?.past_injury_ids || []).map(id=>analysis?.evidence[id]).filter(Boolean);
  const frameCount = Object.values(analysis?.evidence || {}).filter(e=>e.kind==='frame').length;
  return <div className="shell">
    <aside className="rail"><div className="mark" aria-label="PitchGuard">P<span>↗</span></div><div className="rail-line"/>
      <div className="rail-icon on" title="Replay intelligence">▣</div><div className="rail-caption">REPLAY</div><div className="rail-bottom">PG<br/>01</div></aside>
    <main>
      <header><a className="brand" href="/">PITCHGUARD<span>AI</span></a><span className="header-divider"/><span className="header-sub">MATCH INTELLIGENCE</span>
        <div className="header-right"><span className="status-dot"/> {health?.model_configured?'FOUNDRY CONNECTED':'LOCAL WORKSPACE'}<span className="pill">SYNTHETIC DEMO</span></div></header>
      <section className="page-heading"><div><div className="eyebrow">THE EVIDENCE BEHIND THE MOMENT</div><h1>A closer look at the game.</h1><p>Observe the replay. Investigate the evidence. Keep uncertainty in view.</p></div>
        <div className="audience" aria-label="Audience"><button className={audience==='analyst'?'chosen':''} onClick={()=>setAudience('analyst')}>Analyst</button><button className={audience==='fan'?'chosen':''} onClick={()=>{setAudience('fan');setWorkspace('replay');}}>Fan view</button></div></section>
      {audience==='fan'&&<p className="audience-note">Fan view shows public visual evidence only. Switch to Analyst to see player history and the historical assessment.</p>}
      {!health?.local_only && <div className="token-bar"><p>Browse saved analyses and probability simulations freely. An analysis code unlocks up to 10 new analyses; saved results and cached calls do not use the allowance.</p><label>Analysis code <input type="password" value={token} onChange={e=>{setToken(e.target.value);setAllowance(null);}} placeholder="Enter your analysis code" autoComplete="off"/></label><button onClick={async()=>{try{setAllowance(await api('/api/access'));setError('');}catch(e){setAllowance(null);setError(e.message);}}} disabled={!token}>Unlock analysis</button><p>Please contact email: <a href="mailto:cys620999@gmail.com">cys620999@gmail.com</a> if you need test code</p>{allowance&&<p role="status">{allowance.remaining} available · {allowance.used} used · {allowance.pending} reserved. An uncached model request uses one analysis even if it later fails.</p>}</div>}
      {error && <div className="error" role="alert">{error}</div>}
      {audience==='analyst'&&<nav className="workspace-tabs" aria-label="Workspace"><button className={workspace==='replay'?'chosen':''} onClick={()=>setWorkspace('replay')}>1 · Movement evidence</button><button className={workspace==='paired'?'chosen':''} onClick={()=>setWorkspace('paired')}>2 · Paired probability demo</button></nav>}
      {workspace==='paired'&&audience==='analyst'?<PairedDemo/>:<div className="workspace">
        <section className="replay-column">
          {gaitPair&&<div className="gait-intro"><span className="eyebrow">FEATURED COMPARISON · S006 + S004</span><h2>Same speed. A different gait.</h2><p>Matched synthetic clips share speed, path and camera. Compare the steps after 5 seconds. Authored movement differences are not a diagnosis.</p></div>}
          <div className="panel replay-panel"><div className="panel-heading"><div><span className="live-square"/> REPLAY ROOM <span className="muted">/ P001 · Centre-back</span></div><span className="mono">{clock((scenario?.match_start_ms || 4080000)+time*1000)}</span></div>
            <div className={gaitPair?'gait-videos':''}><div><div className="gait-label">{sid} · Selected for analysis</div><div className="video-wrap"><video key={sid} ref={video} src={scenario?.video_url || undefined} controls playsInline preload="metadata" onTimeUpdate={e=>setTime(e.currentTarget.currentTime)} onSeeked={e=>{if(gaitPair&&comparison.current&&Math.abs(comparison.current.currentTime-e.currentTarget.currentTime)>.1)comparison.current.currentTime=e.currentTarget.currentTime;}}/><div className="video-tag">P001 <span>•</span> SYNTHETIC PLAYER</div>
              {!scenario?.video_url && <div className="video-empty">Replay assets unavailable. Rebuild the local animation.</div>}</div></div>
              {gaitPair&&<div><div className="gait-label">{comparisonId} · Matched comparison</div><div className="video-wrap"><video key={comparisonId} ref={comparison} src={comparisonScenario?.video_url || undefined} controls playsInline preload="metadata" aria-label="Matched gait comparison"/>{!comparisonScenario?.video_url&&<div className="video-empty">Comparison assets unavailable.</div>}</div></div>}</div>
            {gaitPair&&<div className="gait-controls"><button onClick={playPair} disabled={!scenario?.video_url||!comparisonScenario?.video_url}>Play both from 5s</button><button onClick={()=>[video.current,comparison.current].forEach(v=>v?.pause())}>Pause both</button><span>Analysis and citations apply to {sid}. Model recognition of this pair is not yet validated.</span></div>}
            <div className="timeline"><span>68:00</span><div className="timeline-track"><i style={{width:`${Math.min(time/10*100,100)}%`}}/>{[0,2,4,6,8,10].map(t=><button key={t} style={{left:`${t*10}%`}} onClick={()=>{if(video.current)video.current.currentTime=t;}} aria-label={`Seek to ${t} seconds`}/>)}</div><span>68:10</span></div>
            <div className="replay-footer"><span>10s observation window <span className="subtle">· 24 fps source</span></span><span>Sampled frames, not continuous tracking</span></div>
          </div>
          <div className="control-row"><div className="scenario-tabs" aria-label="Replay selection">{scenarios.filter(s=>['S006','S004'].includes(s.id)).map(s=><button key={s.id} className={sid===s.id?'selected':''} onClick={()=>setSid(s.id)}><small>{s.id}</small>{s.name}</button>)}</div>
            <button className="analyze" onClick={analyze} disabled={active || !scenario?.available || (!health?.local_only&&!allowance)}>{active?'Analyzing…':'Analyze replay'} <span>↗</span></button></div>
          <details className="more-replays" open={!gaitPair}><summary>More replays · speed examples and occlusion</summary><div className="scenario-tabs">{scenarios.filter(s=>!['S006','S004'].includes(s.id)).map(s=><button key={s.id} className={sid===s.id?'selected':''} onClick={()=>setSid(s.id)}><small>{s.id}</small>{s.name}</button>)}</div><p>S001/S002 support the probability demonstration. S003 adds an occluded view for discussion.</p></details>
          <div className="under-grid"><div className="panel reference-panel"><div className="panel-heading">REFERENCE WINDOW <span className="muted">67:00–67:03</span></div><video ref={reference} src={scenario?.reference_video_url} controls playsInline preload="metadata"/><p>Same synthetic player. Independent reference clip.</p></div>
            <div className="panel context-panel"><div className="panel-heading">CASE CONTEXT <span className="tiny-label">FIXED INPUT</span></div><dl><div><dt>Player</dt><dd>P001 / CB</dd></div><div><dt>Match date</dt><dd>{scenario?.match_date || '—'}</dd></div>{audience==='analyst'&&<div><dt>History cutoff</dt><dd>{scenario?.history_cutoff || '—'}</dd></div>}<div><dt>Analysis</dt><dd>Qualitative review</dd></div></dl><p>Animation and historical records are independent synthetic assets linked for this demonstration.</p></div></div>
          {audience==='analyst'&& <section className="panel history-panel" aria-label="Player history assessment">
            <div className="panel-heading">HISTORY ANALYST <span className="state">{historyStatus}</span></div>
            <p>Player P001 · History through {analysis?.history?.history_cutoff || scenario?.history_cutoff || '—'}. Complete days before the match only.</p>
            {!analysis&&<p>Click Analyze replay or open a saved analysis to load historical metrics and the agent assessment.</p>}
            {historyError&&<div className="error">History branch failed: {historyError}</div>}
            <div className="metric-grid">{[['7-day workload',metric('srpe_load_7d'),'AU'],['Previous 7 days',metric('srpe_load_previous_7d'),'AU'],['Appearances / 14d',metric('actual_appearances_14d'),'played'],['Sleep / 7d mean',metric('sleep_duration_7d_mean'),'hours']].map(([name,n,u])=><div key={name}><span>{name}</span><strong>{n??'—'}<small>{u}</small></strong></div>)}</div>
            {analysis?.history_output&&<div className="history-agent-output"><h3>Historical Agent assessment</h3>
              {analysis.history_output.observations.map((c,i)=><article className="history-agent-claim" key={i}><p>{c.text}</p>{citations(c.evidence_ids)}</article>)}
              {analysis?.decision?<p className="history-participation">Included in investigator input · {acceptedHistory.length} historical sources accepted in the decision.</p>:<p>Assessment available. Final investigator decision is not available yet.</p>}
              {historyCall?.cache_hit&&<p>Cached assessment from an earlier real model call for the same historical input; no new history inference charge.</p>}
            </div>}
            {analysis?.history&&<details className="history-details"><summary>All historical metrics and prior events</summary>
              <div className="history-table-wrap"><table><thead><tr><th>Metric</th><th>Value</th><th>Unit</th></tr></thead><tbody>{metrics.map(m=><tr key={m.name}><th scope="row">{label(m.name)}</th><td>{m.value??'Unavailable'}</td><td>{m.unit}</td></tr>)}</tbody></table></div>
              <h3>Prior events known at the cutoff</h3>
              {priorInjuries.length?priorInjuries.map(e=><article className="history-agent-claim" key={e.id}><p>{e.values.injury_start_date} · {e.values.injury_type} · {e.values.body_location}</p>{citations([e.id])}</article>):<p>No prior events available in this case.</p>}
              {(analysis.history_output?.limitations || analysis.history.limitations || []).map((text,i)=><p key={i}>{text}</p>)}
            </details>}
            <p>Historical context informs review; it does not establish a diagnosis or calibrated injury probability.</p>
          </section>}
        </section>
        <aside className="insight-column"><div className="panel insights"><div className="panel-heading">EVIDENCE DESK <span className={`state ${active?'working':''}`}>{label(analysis?.state || 'ready')}</span></div>
          <div className="insight-top"><span className="eyebrow">{audience==='analyst'?'ANALYST BRIEF':'FROM THE TOUCHLINE'}</span><h2>{narrative?.headline || (active?'Following the evidence…':'Every observation needs a source.')}</h2><p>{analysis?`${cached?'Saved analysis · ':''}${analysis.elapsed_seconds?analysis.elapsed_seconds+'s processing · ':''}${frameCount} evidence frames`:'Run an analysis to compare visible movement with a reference and inspect the supporting evidence.'}</p>{analysis&&<p>Machine output · human validation pending<br/>Input revision {analysis.input_revision.slice(0,12)}</p>}</div>
          {narrative?.statements?.map((c,i)=><article className="claim" key={i}><span className="claim-number">0{i+1}</span><div><p>{c.text}</p>{citations(c.evidence_ids)}</div></article>)}
          {!narrative&&active&&<div className="processing"><span className="pulse"/>History + motion → investigation → publication</div>}
          {analysis?.error&&<div className="error">{analysis.error}</div>}
          {audience==='analyst'&&!narrative&&['history_output','motion_output'].map(key=>analysis?.[key]?.observations?.map((c,i)=><article className="claim" key={key+i}><div><small>PARTIAL RESULT · {key}</small><p>{c.text}</p>{citations(c.evidence_ids)}</div></article>))}
          {!!narrative?.limitations?.length&&<div className="limitations"><span>WHAT REMAINS UNKNOWN</span>{narrative.limitations.map((v,i)=><p key={i}>{v}</p>)}</div>}
          <div className="prototype-note"><span>◈</span><p>Synthetic replay analysis. Qualitative observations only. No medical assessment or validated injury probability.</p></div>
          {audience==='analyst'&&analysis&&!analysis.public_demo&&(health?.local_only||allowance)&&<button className="acknowledge" disabled={ack} onClick={async()=>{try{await api(`/api/analyses/${caseId}/acknowledgements`,{method:'POST'});setAck(true);}catch(e){setError(e.message);}}}>{ack?'✓ Review recorded':'Mark as reviewed'} <span>↗</span></button>}
        </div>
        {selected&&<div className="panel evidence-detail"><div className="panel-heading">SOURCE EVIDENCE <button onClick={()=>setSelected(null)} aria-label="Close evidence">×</button></div><strong>{selected.id}</strong>{selected.kind==='frame'?<><img src={selected.image_url} alt={`Evidence ${selected.id}`}/><p>Clip {(selected.clip_time_ms/1000).toFixed(2)}s · Match {clock(selected.match_time_ms)}</p><p>Source SHA-256: <code>{selected.source_sha256.slice(0,16)}…</code></p></>:<><p>{selected.source_file} · CSV line {selected.csv_line || 'indexed'}</p><pre>{JSON.stringify(selected.values,null,2)}</pre></>}</div>}
        {calls.length>0&&<div className="panel trace-panel"><div className="panel-heading">ACTUAL CALLS <span className="muted">{calls.filter(c=>!c.cache_hit).length} new · {calls.filter(c=>c.cache_hit).length} cached</span></div>{calls.map((c,i)=><div className="trace-row" key={i}><span className={c.status==='completed'?'check':'muted'}>{c.status==='completed'?'✓':'·'}</span><strong>{label(c.role)}</strong><small>{c.cache_hit?'CACHE':c.status==='completed'?`${c.latency_seconds}s`:c.status}</small></div>)}{audience==='analyst'&&<p>Cost: {calls.some(c=>c.cost_status==='unknown_rates')?'not calculated — unit prices not configured':'see exported usage'}. Cached calls incur no new inference charge.</p>}</div>}
        </aside>
      </div>}
      <footer><span>PITCHGUARD AI <span className="subtle">/ Evidence before conclusions.</span></span>{workspace==='replay'&&<label>Workflow <select value={mode} onChange={e=>setMode(e.target.value)} disabled={active}><option value="multi">Specialists + investigator</option><option value="single">Single analyst baseline (experimental)</option></select></label>}<span className="subtle">POWERED BY MICROSOFT FOUNDRY</span></footer>
    </main>
  </div>;
}

createRoot(document.getElementById('root')).render(<App/>);
