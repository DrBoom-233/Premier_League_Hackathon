import React, {useEffect, useState} from 'react';

const pct = value => value == null ? 'Unavailable' : `${(value * 100).toFixed(1)}%`;

export default function PairedDemo({token}) {
  const [data, setData] = useState(null), [selected, setSelected] = useState('DEMO05');
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
  const gait = item?.comparison_group==='gait';
  if (error) return <div className="error" role="alert">{error}</div>;
  if (!item) return <p>Loading paired simulation…</p>;
  return <section className="paired-demo" aria-label="Paired probability simulation">
    <div className="panel paired-intro"><span className="eyebrow">A CONTROLLED WHAT-IF DEMONSTRATION</span>
      <h2>History and video, together.</h2>
      <p>Start with S006, then select S004: identical history, matched speed and path, different measured step patterns. Inspect how video changes the simulator probability.</p>
      <p className="paired-disclosure">Illustrative simulator probabilities. No model training or clinical validation. These numbers describe the specified synthetic event process.</p>
    </div>
    <div className="paired-options" role="group" aria-label="Featured gait pair">{data.cases.filter(c=>c.comparison_group==='gait').map(c=><button key={c.id} className={c.id===selected?'chosen':''} onClick={()=>setSelected(c.id)} aria-pressed={c.id===selected}>{c.title}</button>)}</div>
    <details className="more-replays"><summary>More probability examples · S001/S002 speed comparison</summary><div className="paired-options" role="group" aria-label="Speed case selection">{data.cases.filter(c=>c.comparison_group==='speed').map(c=><button key={c.id} className={c.id===selected?'chosen':''} onClick={()=>setSelected(c.id)} aria-pressed={c.id===selected}>{c.title}</button>)}</div></details>
    <div className="paired-grid">
      <div className="panel"><div className="panel-heading">CURRENT REPLAY <span className="muted">{item.id} / AVATAR P001</span></div>
        <video key={item.video_url} src={item.video_url} controls playsInline preload="metadata" aria-label="Paired current replay" onLoadedMetadata={e=>{if(gait)e.currentTarget.currentTime=5;}}/>
        <div className="paired-copy"><p>Same avatar and camera. The probability uses movement measured from decoded video pixels.</p>
          <p>Reference animation · shared across the six fictional worlds{gait?' · not used by the shoe-span measurement':''}</p>
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
            <div><dt>{gait?'Step-span variation / 5–10s':'Late speed / reference'}</dt><dd>{gait?item.visual.step_span_variation.toFixed(4):pct(item.visual.late_speed_ratio)}</dd></div>
            <div><dt>History through</dt><dd>{item.history.cutoff} · 28 complete days</dd></div></dl>
          <p>Prediction origin: {item.as_of.replace('T',' ').replace('+00:00',' UTC')}<br/>Follow-up ends: {item.target_end.replace('T',' ').replace('+00:00',' UTC')}</p>
          <p>{gait?'The simulator assigns a higher event rate when measured step-span variation reaches 0.12. This threshold and rate are illustrative, not medically calibrated.':'Slowing is a stipulated factor in this toy simulator. It is not evidence that slowing predicts real-world injury.'} A higher probability does not mean an event must occur.</p>
          <p>The generator uses mean fatigue and measured motion. Workload and sleep are shown as context.</p>
          <details><summary>Inspect video measurements</summary>{gait&&<p>Variation = standard deviation / mean of successive shoe-separation peaks. Pixel peaks: {item.visual.peak_spans_px.map(v=>v.toFixed(1)).join(', ')} px. A visual proxy for these authored clips; no anatomical diagnosis.</p>}<table><thead><tr><th>Clip time</th><th>{gait?'Shoe separation':'Avatar position'}</th></tr></thead><tbody>{item.visual.samples.map(s=><tr key={s.frame}><td>{(s.time_ms/1000).toFixed(2)}s</td><td>{(gait?s.shoe_span_px:s.centroid_x).toFixed(1)} px</td></tr>)}</tbody></table><p>Fixed-camera pixel measurement · {item.visual.extractor_version}</p></details>
        </div>
      </div>
    </div>
    <div className="panel paired-copy paired-limits"><p>Demo scope: 6 what-if cases · 2 history profiles · 4 unique current videos · 1 shared reference · 0 new model calls.</p>
      <p>The history-only estimate averages the two stipulated motion states. The joint estimate conditions on the observed replay. Neither estimate is fitted to medical outcomes.</p>
      <p>Future event draws are kept offline. The original replay Agent workflow remains a separate qualitative analysis.</p>
    </div>
  </section>;
}
