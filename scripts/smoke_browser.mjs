import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import assert from 'node:assert/strict';
import {chromium} from '../frontend/node_modules/playwright/index.mjs';
const root=path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const origin=process.env.AWAAZ_BASE_URL||'https://awaazsetu.vercel.app';
const password=fs.readFileSync(path.join(root,'.env'),'utf8').split('\n').find(s=>s.startsWith('ADMIN_PASSWORD=')).slice(15);
const browser=await chromium.launch({channel:'chrome',headless:true});
const context=await browser.newContext({viewport:{width:1440,height:1000}});
const page=await context.newPage();
const errors=[];page.on('pageerror',e=>errors.push(e.message));
const checks=[];
async function checked(name,fn){await fn();checks.push(name);console.log('PASS:',name)}
try{
 await checked('Public incident APIs require coordinator auth',async()=>{const r=await context.request.get(origin+'/api/incidents');assert.equal(r.status(),401)});
 await page.goto(origin,{waitUntil:'networkidle'});
 await checked('Resident form is localized Marathi by default',async()=>{await page.getByRole('heading',{name:'घटनेची माहिती द्या'}).waitFor()});
 fs.mkdirSync(path.join(root,'work/screenshots'),{recursive:true});
 await page.screenshot({path:path.join(root,'work/screenshots/resident-desktop.png'),fullPage:true});
 await page.locator('select').first().selectOption('en');
 await page.locator('textarea').fill('DRILL ONLY hosted browser verification: Water entering home at Warje. Nobody is trapped.');
 await page.getByRole('checkbox').check();
 await page.getByRole('button',{name:'Send report',exact:true}).click();
 await checked('Real hosted text intake and private tracking link',async()=>{await page.getByRole('heading',{name:'Your voice has been received'}).waitFor({timeout:60000});await page.getByRole('link',{name:'Track your report'}).click();await page.getByRole('heading',{name:'Follow your ticket.'}).waitFor({timeout:10000})});
 const trackURL=page.url();
 await page.goto(origin);await page.locator('select').first().selectOption('en');
 await page.locator('input[type=file]').setInputFiles(path.join(root,'work/voice-demo.wav'));
 // The original consent checkbox remains the only checkbox before transcript review.
 await page.getByRole('checkbox').first().check();
 await page.getByRole('button',{name:'Transcribe and review',exact:true}).click();
 await page.getByLabel('I reviewed this transcript and corrected any errors.').waitFor({timeout:60000});
 await checked('Real hosted editable voice preview before report creation',async()=>{assert.match(await page.locator('textarea').inputValue(),/flood drill/i)});
 await page.getByLabel('I reviewed this transcript and corrected any errors.').check();
 await page.getByRole('button',{name:'Send report',exact:true}).click();
 await page.getByRole('heading',{name:'Your voice has been received'}).waitFor({timeout:60000});
 await checked('Reviewed voice text creates a real ticket',async()=>{assert(await page.getByRole('link',{name:'Track your report'}).isVisible())});

 await page.goto(origin+'/console');
 await page.getByLabel('Coordinator password').fill(password);
 await page.getByRole('button',{name:'Enter console'}).click();
 await checked('Real coordinator login and private incident map',async()=>{await page.locator('.map').waitFor({timeout:30000});await page.locator('.queue-card').waitFor()});
 await page.goto(origin+'/console/settings');
 await page.getByRole('button',{name:'Load drill examples'}).click();
 await page.locator('.success-note').waitFor({timeout:60000});
 await checked('Idempotent synthetic drill dataset available',async()=>{assert.match(await page.locator('.success-note').innerText(),/Drill dataset ready/)});
 await page.goto(origin+'/console');
 await page.locator('.row-title').first().waitFor();
 await page.screenshot({path:path.join(root,'work/screenshots/console-desktop.png'),fullPage:true});
 await page.locator('.row-title').first().click();
 await checked('Incident details include scoring reasons and original reports',async()=>{await page.getByRole('heading',{name:'Why this priority?'}).waitFor();await page.locator('.source-report').first().waitFor()});
 await page.getByLabel('Notes',{exact:true}).fill('Hosted automated drill: source text reviewed by test coordinator.');
 const verified=page.getByRole('button',{name:'verified',exact:true});
 if(await verified.isEnabled()){await verified.click();await page.waitForTimeout(800)}
 await page.getByRole('button',{name:'Close detail'}).click();
 for(const [route,heading] of [['coverage','Who are we hearing from?'],['notifications','Keep the connection open.'],['settings','Know what is connected.']]){
  await page.goto(origin+'/console/'+route);await checked('Hosted '+route+' page',async()=>{await page.getByRole('heading',{name:heading}).waitFor();assert.equal(await page.getByRole('alert').count(),0)});
 }
 await page.setViewportSize({width:390,height:844});
 await page.goto(origin+'/console');await page.locator('.map').waitFor();
 await checked('390px mobile console has no page overflow',async()=>{assert(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth+1))});
 await page.screenshot({path:path.join(root,'work/screenshots/console-mobile.png'),fullPage:true});
 await page.goto(origin);await page.getByRole('heading',{name:'घटनेची माहिती द्या'}).waitFor();
 await checked('390px mobile resident form has no page overflow',async()=>{assert(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth+1))});
 await page.screenshot({path:path.join(root,'work/screenshots/resident-mobile.png'),fullPage:true});
 await checked('No browser runtime errors',async()=>assert.deepEqual(errors,[]));
 fs.writeFileSync(path.join(root,'work/browser-validation.json'),JSON.stringify({origin,checked_at:new Date().toISOString(),checks,errors,tracking_checked:true},null,2));
 console.log('Hosted browser workflow completed. Private tokens/passwords were not printed.');
}finally{await browser.close()}
