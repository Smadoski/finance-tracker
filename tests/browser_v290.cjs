const {chromium,webkit}=require('playwright');
const fs=require('fs');const assert=require('assert');
const base=process.env.FINANCE_TEST_URL;
if(!base || !/^http:\/\/(127\.0\.0\.1|localhost):[0-9]+$/.test(base))throw Error('Set FINANCE_TEST_URL to an isolated synthetic localhost server. Never test production.');
const out=process.env.FINANCE_TEST_OUTPUT||'/tmp';
(async()=>{
 const results=[],errors=[],checks=[];
 for(const engine of ['chromium','webkit']){
  const browser=await (engine==='chromium'?chromium.launch({headless:true,executablePath:process.env.CHROME_PATH||'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'}):webkit.launch({headless:true}));
  for(const [device,width,height] of [['desktop',1440,1000],['ipad',820,1180],['iphone',390,844]]){
   const context=await browser.newContext({viewport:{width,height},isMobile:device!=='desktop',hasTouch:device!=='desktop'});
   await context.addInitScript(()=>{window.shareMode='success';Object.defineProperty(navigator,'canShare',{value:()=>true,configurable:true});Object.defineProperty(navigator,'share',{value:async()=>{if(window.shareMode==='cancel')throw new DOMException('Cancelled','AbortError');if(window.shareMode==='error')throw new Error('Native share failed');},configurable:true});});
   const page=await context.newPage();page.on('pageerror',e=>errors.push({engine,device,error:String(e)}));
   for(const path of ['/','/accounts','/transactions','/pending','/recurring/','/recurring/1/edit','/reports/categories','/reports/recurring','/reports/recurring?monthly=1&annual=1','/planning/upcoming','/planning/forecast','/planning/search','/planning/import','/planning/ai-review','/budgets/report','/quick','/transfer','/settings','/system','/health/','/health/classify','/health/classify?table=accounts','/health/classify?table=recurring_rules','/health/funding','/health/estimated-forecast']){
    const response=await page.goto(base+path);
    checks.push({engine,device,path,status:response.status(),overflow:await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth)});
    if(path==='/health/'||path==='/health/funding'){
     if(path==='/health/funding')await page.locator('details.card').first().locator('summary').first().click();
     assert(!await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),path+' expanded overflow');
     if(engine==='webkit')await page.screenshot({path:out+'/finance-v290-'+device+(path==='/health/'?'-health':'-funding')+'.png',fullPage:true});
    }
   }
   await page.goto(base+'/health/');
   await page.getByText('Income stress test — scenario',{exact:true}).click();
   const initial=await page.locator('#scenario-results').innerText();
   await page.locator('#scenario-preset').selectOption('no_investment');assert.notEqual(await page.locator('#scenario-results').innerText(),initial);
   await page.locator('#scenario-preset').selectOption('current');assert.equal(await page.locator('#scenario-results').innerText(),initial);
   results.push({engine,device,test:'stress presets update and reset'});
   async function navigate(){
    assert.equal(await page.locator('#json-generate').isEnabled(),true);
    if(device!=='desktop')await page.locator('.nav-menu > summary').click();
    await page.getByRole('navigation').getByRole('link',{name:'Accounts',exact:true}).click();
    assert(page.url().endsWith('/accounts'));
   }
   for(const mode of ['success','cancel','error']){
    await page.goto(base+'/planning/ai-review');await page.evaluate(mode=>window.shareMode=mode,mode);
    await page.locator('#json-generate').click();await page.locator('#json-share').waitFor({state:'visible'});
    assert(page.url().endsWith('/planning/ai-review'));await page.locator('#json-share').click();
    await page.waitForFunction(()=>/completed|cancelled|unavailable/.test(document.getElementById('json-status').textContent));
    await navigate();results.push({engine,device,test:'share '+mode+' then navigation'});
   }
   await page.goto(base+'/planning/ai-review');await page.locator('#json-generate').click();await page.locator('#json-download').waitFor({state:'visible'});
   const downloadPromise=page.waitForEvent('download');await page.locator('#json-download').click();const download=await downloadPromise;const file=await download.path();assert(JSON.parse(fs.readFileSync(file)).schema_version==='finance-tracker.financial-review/2.9');
   await navigate();results.push({engine,device,test:'save JSON then navigation'});
   await page.goto(base+'/planning/ai-review');
   await page.route('**/planning/ai-review?**',route=>route.fulfill({status:500,contentType:'text/html',body:'Export failed'}));
   await page.locator('#json-generate').click();await page.waitForFunction(()=>document.getElementById('json-status').textContent.includes('unavailable'));await navigate();
   await page.unroute('**/planning/ai-review?**');results.push({engine,device,test:'export error then navigation'});
   await page.goto(base+'/planning/ai-review');await page.clock.install();
   await page.route('**/planning/ai-review?**',route=>{});
   await page.locator('#json-generate').click();await page.clock.runFor(31000);await page.waitForFunction(()=>document.getElementById('json-status').textContent.includes('timed out'));await navigate();
   results.push({engine,device,test:'export timeout then navigation'});await context.close();
  }
  await browser.close();
 }
 fs.writeFileSync(out+'/finance-v290-browser-results.json',JSON.stringify({checks,results,errors},null,2));
 console.log(JSON.stringify({pages:checks.length,lifecycleChecks:results.length,failures:checks.filter(c=>c.status!==200||c.overflow),errors},null,2));
 assert(!errors.length);assert(checks.every(c=>c.status===200&&!c.overflow));
})().catch(e=>{console.error(e);process.exitCode=1;});
