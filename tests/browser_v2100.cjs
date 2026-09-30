const {chromium,webkit}=require('playwright');
const fs=require('fs'),assert=require('assert');
const base=process.env.FINANCE_TEST_URL,out=process.env.FINANCE_TEST_OUTPUT||'/tmp';
if(!/^http:\/\/(127\.0\.0\.1|localhost):[0-9]+$/.test(base||''))throw Error('Use an isolated synthetic localhost fixture.');
(async()=>{
 const checks=[],errors=[];
 for(const engine of ['chromium','webkit']){
  const browser=await (engine==='chromium'?chromium.launch({headless:true,executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'}):webkit.launch({headless:true}));
  for(const [device,width,height] of [['desktop',1440,1000],['ipad',820,1180],['iphone',390,844]]){
   const context=await browser.newContext({viewport:{width,height},isMobile:device!=='desktop',hasTouch:device!=='desktop'});
   const page=await context.newPage();page.on('pageerror',e=>errors.push(String(e)));
   for(const path of ['/','/reports/overview','/account/3','/account/3/edit','/accounts','/transactions','/quick','/pending','/transfer','/settings','/planning/forecast','/health/estimated-forecast','/reports/recurring']){
    const response=await page.goto(base+path);assert.equal(response.status(),200,path);
    if(path==='/accounts'||path==='/transactions')await page.locator('details.disclosure > summary').click();
    assert(!await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),engine+' '+device+' '+path+' overflow');
    checks.push({engine,device,path});
    if(path==='/'){
     const fav=page.locator('.favourite-account');assert.equal(await fav.count(),2);
     assert(await fav.first().innerText().then(t=>t.includes('First Direct')));
     const second=await fav.nth(1).boundingBox();assert(second.y+second.height<height,'Both favourite balances visible without scrolling');
     assert.equal(await page.locator('.home-recent-row').count(),5);
     await page.screenshot({path:out+'/finance-v2100-'+engine+'-'+device+'-home.png',fullPage:true});
     await page.getByText('Combined position',{exact:true}).click();
     assert(await page.getByText('Cash less liabilities:',{exact:false}).isVisible());
     await page.getByRole('link',{name:'Reports & Insights',exact:true}).click();assert(page.url().endsWith('/reports/overview'));
    }
    if(path==='/account/3/edit')assert.equal(await page.locator('[name=account_type]').inputValue(),'credit_card');
    if(path==='/transactions')assert(await page.locator('[name=account_id]').innerText().then(t=>t.includes('Everyday card')));
    if(path==='/planning/forecast')assert(await page.getByRole('heading',{name:'Credit-card debt forecast'}).isVisible());
   }
   await page.goto(base+'/');if(device!=='desktop')await page.locator('.nav-menu > summary').click();
   await page.getByRole('navigation').getByRole('link',{name:'Reports',exact:true}).click();
   assert.equal(await page.locator('nav [aria-current=page]').textContent(),'Reports');
   await context.close();
  }
  await browser.close();
 }
 fs.writeFileSync(out+'/finance-v2100-browser-results.json',JSON.stringify({checks,errors},null,2));
 console.log(JSON.stringify({pages:checks.length,errors}));assert.equal(errors.length,0);
})().catch(e=>{console.error(e);process.exit(1)});
