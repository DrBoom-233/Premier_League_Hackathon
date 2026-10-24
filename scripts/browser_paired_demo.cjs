// Real local UI/media checks. This script must never trigger paid analysis.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const {chromium} = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const base = process.env.PITCHGUARD_BASE_URL || 'http://127.0.0.1:8000';
(async()=>{
  const browser = await chromium.launch({headless:true, channel:process.env.BROWSER_CHANNEL || 'msedge'});
  try {
    const page = await browser.newPage({viewport:{width:1440,height:1100}});
    const errors=[];let paidPosts=0;
    page.on('pageerror',e=>errors.push(e.message));
    page.on('request',r=>{if(r.method()==='POST'&&r.url().endsWith('/api/analyses'))paidPosts++;});
    const response=await page.request.get(base+'/api/demo/paired');
    assert.equal(response.status(),200);
    const data=await response.json();
    assert.equal(data.cases.length,4);
    for(const field of ['label_7d','generator_probability','future_event'])assert(!JSON.stringify(data).includes(field));
    await page.goto(base+'/?view=paired');
    const region=page.getByRole('region',{name:'Paired probability simulation'});
    await region.getByText('History and video, together.',{exact:true}).waitFor();
    for(const item of data.cases){
      await region.getByRole('button',{name:item.title,exact:true}).click();
      assert.equal(await region.getByTestId('joint-probability').innerText(),(item.probability.value*100).toFixed(1)+'%');
      assert.equal(await region.getByTestId('history-probability').innerText(),(item.probability.history_only_value*100).toFixed(1)+'%');
      await page.waitForFunction(()=>document.querySelector('video[aria-label="Paired current replay"]')?.readyState>=1);
      assert.equal(await region.getByLabel('Paired current replay').evaluate(v=>v.duration),10);
    }
    assert.equal(data.cases[0].probability.history_only_value,data.cases[1].probability.history_only_value);
    assert.notEqual(data.cases[0].probability.value,data.cases[1].probability.value);
    await region.getByRole('button',{name:data.cases[1].title,exact:true}).click();
    await page.waitForFunction(()=>[...document.querySelectorAll('video')].every(v=>v.readyState>=2&&!v.seeking));
    for(const name of ['Paired current replay','Paired reference replay']){
      const video=region.getByLabel(name);
      await video.evaluate(async v=>{v.muted=true;await v.play();});
      await page.waitForFunction(label=>document.querySelector(`video[aria-label="${label}"]`).currentTime>.15,name);
      await video.evaluate(v=>{v.pause();v.currentTime=v.duration>5?7:1.5;});
    }
    await page.waitForFunction(()=>[...document.querySelectorAll('video')].every(v=>v.readyState>=2&&!v.seeking&&v.paused));
    fs.mkdirSync('.tools',{recursive:true});
    await page.screenshot({path:'.tools/paired-demo-desktop.png',fullPage:true});
    await region.getByText('Inspect video measurements',{exact:true}).click();
    assert.equal(await region.locator('tbody tr').count(),7);
    await page.setViewportSize({width:390,height:844});
    assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
    await page.screenshot({path:'.tools/paired-demo-mobile.png',fullPage:true});
    await page.getByRole('button',{name:'Fan view',exact:true}).click();
    assert.equal(await page.getByRole('region',{name:'Paired probability simulation'}).count(),0);
    assert.equal(await page.getByRole('button',{name:'Paired probability demo',exact:true}).count(),0);
    assert.equal(paidPosts,0);assert.deepEqual(errors,[]);
    console.log('PASS: four paired cases, exact probabilities, real video metadata, pixel evidence, mobile, fan hiding; zero paid POST.');
  } finally {await browser.close();}
})().catch(error=>{console.error(error);process.exit(1);});
