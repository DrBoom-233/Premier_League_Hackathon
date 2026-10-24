import React, {useEffect, useState} from 'react';

const pct = value => value == null ? 'Unavailable' : `${(value * 100).toFixed(1)}%`;

export default function PairedDemo({token}) {
  const [data, setData] = useState(null), [selected, setSelected] = useState('DEMO02');
  const [error, setError] = useState('');
  useEffect(()=>{
    let cancelled = false;
    setData(null);setError('');
    fetch('/api/demo/paired', {headers: token ? {'X-Analyst-Token': token} : {}})
      .then(async response=>{
        const body = await response.json();
        if (!response.ok) throw new Error(body.detail || 'Paired demo unavailable');
        if (!cancelled) setData(body);
      }).catch(e=>{if(!cancelled)setError(e.message);});
    return ()=>{cancelled=true;};
  },[token]);
  const item = data?.cases.find(c=>c.id===selected);
  if (error) return <div className="error" role="alert">{error}</div>;
  if (!item) return <p>Loading paired simulation…</p>;
  return <section className="paired-demo" aria-label="Paired probability simulation">
    <div className="panel paired-intro"><span className="eyebrow">A CONTROLLED WHAT-IF DEMONSTRATION</span>
      <h2>History and video, together.</h2>
      <p>Four fictional worlds combine two history profiles with two replay templates. Change the replay while keeping history fixed to inspect its contribution.</p>
      <p className="paired-disclosure">Illustrative simulator probabilities. No model training or clinical validation. These numbers describe the specified synthetic event process.</p>
    </div>
    <div className="paired-options" role="group" aria-label="Paired case selection">{data.cases.map(c=><button key={c.id} className={c.id===selected?'chosen':''} onClick={()=>setSelected(c.id)} aria-pressed={c.id===selected}>{c.title}</button>)}</div>
    <div className="paired-grid">
      <div className="panel"><div className="panel-heading">CURRENT REPLAY <span className="muted">{item.id} / AVATAR P001</span></div>
        <video key={item.video_url} src={item.video_url} controls playsInline preload="metadata" aria-label="Paired current replay"/>
        <div className="paired-copy"><p>Same avatar and camera. The probability uses movement measured from decoded video pixels.</p>
          <p>Reference animation · shared across the four fictional worlds</p>
          <video className="paired-reference" src={item.reference_video_url} controls playsInline preload="metadata" aria-label="Paired reference replay"/>
        </div>
      </div>
      <div className="panel paired-results"><div className="panel-heading">7-DAY NON-CONTACT INJURY <span className="tiny-label">SIMULATED</span></div>
        <div className="paired-copy">
          <div className="paired-probabilities"><div><span>History only</span><strong data-testid="history-probability">{pct(item.probability.history_only_value)}</strong></div>
            <div><span>History + video</span><strong data-testid="joint-probability">{pct(item.probability.value)}</strong></div></div>
          <p>{item.probability.video_used?'Video participated · measured movement':'Video unavailable · joint estimate unavailable'}</p>
          <dl className="paired-metrics"><div><dt>Mean fatigue / 7d</dt><dd>{item.history.fatigue_7d_mean.toFixed(1)} / 5</dd></div>
            <div><dt>Workload / 7d</dt><dd>{item.history.srpe_load_7d} AU</dd></div>
            <div><dt>Sleep / 7d</dt><dd>{item.history.sleep_7d_mean} hours</dd></div>
            <div><dt>Late speed / reference</dt><dd>{pct(item.visual.late_speed_ratio)}</dd></div>
            <div><dt>History through</dt><dd>{item.history.cutoff} · 28 complete days</dd></div></dl>
          <p>Prediction origin: {item.as_of.replace('T',' ').replace('+00:00',' UTC')}<br/>Follow-up ends: {item.target_end.replace('T',' ').replace('+00:00',' UTC')}</p>
          <p>Slowing is a stipulated factor in this toy simulator. It is not evidence that slowing predicts real-world injury. A higher probability does not mean an event must occur.</p>
          <p>The generator uses mean fatigue and measured motion. Workload and sleep are shown as context.</p>
          <details><summary>Inspect video measurements</summary><table><thead><tr><th>Clip time</th><th>Avatar position</th></tr></thead><tbody>{item.visual.samples.map(s=><tr key={s.frame}><td>{(s.time_ms/1000).toFixed(2)}s</td><td>{s.centroid_x.toFixed(1)} px</td></tr>)}</tbody></table><p>Fixed-camera blue-avatar tracker · {item.visual.extractor_version}</p></details>
        </div>
      </div>
    </div>
    <div className="panel paired-copy paired-limits"><p>Demo scope: 4 what-if cases · 2 history profiles · 2 unique current videos · 1 shared reference · 0 new model calls.</p>
      <p>The history-only estimate averages the two stipulated motion states. The joint estimate conditions on the observed replay. Neither estimate is fitted to medical outcomes.</p>
      <p>Future event draws are kept offline. The original replay Agent workflow remains a separate qualitative analysis.</p>
    </div>
  </section>;
}
