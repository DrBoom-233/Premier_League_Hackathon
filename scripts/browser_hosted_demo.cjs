// Read-only acceptance of the public judge flow; never submit a model request.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const {chromium} = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const base = process.env.PITCHGUARD_BASE_URL || 'http://127.0.0.1:8012';
(async()=>{
  const browser = await chromium.launch({headless:true,channel:'msedge'});
  try {
    const page = await browser.newPage({viewport:{width:1440,height:1050}});
    let posts=0;const errors=[];
    page.on('request',r=>{if(r.method()==='POST'&&r.url().endsWith('/api/analyses'))posts++;});
    page.on('pageerror',e=>errors.push(e.message));
    await page.goto(base);
    await page.getByText('Machine output · human validation pending').waitFor();
    assert.match(await page.locator('.insight-top').innerText(),/Saved analysis/);
    assert.match(await page.locator('.gait-label').first().innerText(),/S006/);
    await page.waitForFunction(()=>[...document.querySelectorAll('.gait-videos video')].every(v=>v.readyState>=2),null,{timeout:45000});
    await page.getByRole('button',{name:'Play both from 5s'}).click();
    await page.waitForFunction(()=>[...document.querySelectorAll('.gait-videos video')].every(v=>!v.paused&&v.currentTime>5.1));
    await page.getByRole('button',{name:'Pause both',exact:true}).click();
    assert(await page.getByRole('button',{name:'Analyze replay'}).isDisabled());
    assert.equal(await page.getByRole('link',{name:'cys620999@gmail.com'}).getAttribute('href'),'mailto:cys620999@gmail.com');
    assert.match(await page.locator('.token-bar').innerText(),/Please contact email: cys620999@gmail.com if you need test code/);
    if(process.env.PITCHGUARD_TEST_CODE) {
      await page.getByPlaceholder('Enter your analysis code').fill(process.env.PITCHGUARD_TEST_CODE);
      await page.getByRole('button',{name:'Unlock analysis'}).click();
      await page.getByRole('status').filter({hasText:/available/}).waitFor();
      assert.equal(await page.getByRole('button',{name:'Analyze replay'}).isEnabled(),true);
    }
    await page.getByRole('button',{name:/Paired probability demo/}).click();
    await page.getByTestId('history-probability').waitFor();
    await page.getByRole('button',{name:'Fan view',exact:true}).click();
    assert.equal(await page.getByRole('region',{name:'Player history assessment'}).count(),0);
    await page.getByRole('button',{name:'Analyst',exact:true}).click();
    await page.getByText('Historical Agent assessment',{exact:true}).waitFor();
    fs.mkdirSync('.tools',{recursive:true});
    await page.screenshot({path:'.tools/hosted-desktop.png',fullPage:true});
    await page.setViewportSize({width:390,height:844});
    assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
    await page.screenshot({path:'.tools/hosted-mobile.png',fullPage:true});
    assert.equal(posts,0);assert.deepEqual(errors,[]);
    console.log('PASS: public saved S006 analysis, gait videos, paired simulator, analyst/fan filtering, test-code unlock, exact email prompt, mobile; zero analysis POST.');
  } finally {await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
