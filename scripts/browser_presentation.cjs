// Local presentation checks; never submit a paid analysis.
const assert = require('node:assert/strict');
const {chromium} = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const base = process.env.PITCHGUARD_BASE_URL || 'http://127.0.0.1:8000';
(async()=>{
  const browser = await chromium.launch({headless:true,channel:process.env.BROWSER_CHANNEL || 'msedge'});
  try {
    const page = await browser.newPage({viewport:{width:1440,height:1050}});
    const errors=[];let posts=0;
    page.on('pageerror',e=>errors.push(e.message));
    page.on('request',r=>{if(r.method()==='POST'&&r.url().endsWith('/api/analyses'))posts++;});
    await page.goto(base);
    await page.getByRole('button',{name:'Play both from 5s'}).waitFor();
    await page.waitForFunction(()=>[...document.querySelectorAll('.gait-videos video')].every(v=>v.readyState>=2));
    assert.match(await page.locator('.gait-label').first().innerText(),/S006/);
    assert.equal(await page.getByRole('button',{name:/Replay 3/}).isVisible(),false);
    await page.getByRole('button',{name:'Play both from 5s'}).click();
    await page.waitForFunction(()=>[...document.querySelectorAll('.gait-videos video')].every(v=>!v.paused&&v.currentTime>5.1));
    await page.getByRole('button',{name:'Pause both',exact:true}).click();
    const times=await page.locator('.gait-videos video').evaluateAll(vs=>vs.map(v=>({time:v.currentTime,paused:v.paused})));
    assert(times.every(v=>v.paused));assert(Math.abs(times[0].time-times[1].time)<.2);
    await page.waitForFunction(()=>[...document.querySelectorAll('video')].every(v=>v.readyState>=2&&!v.seeking));
    await page.screenshot({path:'.tools/presentation-desktop.png',fullPage:true});
    await page.getByRole('button',{name:/S004.*Replay 4/}).click();
    await page.getByText('Analysis and citations apply to S004.',{exact:false}).waitFor();
    assert.equal(await page.locator('.claim').count(),0);
    await page.setViewportSize({width:390,height:844});
    await page.screenshot({path:'.tools/presentation-mobile.png',fullPage:true});
    assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
    await page.getByText('More replays · speed examples and occlusion',{exact:true}).click();
    await page.getByRole('button',{name:/Replay 3/}).click();
    assert.equal(await page.locator('.gait-videos').count(),0);
    await page.getByRole('button',{name:/Paired probability demo/}).click();
    await page.getByRole('region',{name:'Paired probability simulation'}).waitFor();
    await page.getByRole('button',{name:'Fan view',exact:true}).click();
    assert.equal(await page.getByRole('region',{name:'Paired probability simulation'}).count(),0);
    assert.equal(posts,0);assert.deepEqual(errors,[]);
    console.log('PASS: featured pair playback/pause, selection, secondary replays, probability entry, fan view, mobile; zero paid POST.');
  } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
