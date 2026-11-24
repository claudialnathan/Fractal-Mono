import {createServer} from 'node:http';
import {readFileSync,mkdirSync,writeFileSync} from 'node:fs';
import {resolve,dirname,extname,sep} from 'node:path';
import {fileURLToPath} from 'node:url';
import {createRequire} from 'node:module';
import {chromium} from 'playwright';
const root=resolve(dirname(fileURLToPath(import.meta.url)),'..');
const styles=['Thin','ExtraLight','Light','Regular','Medium','SemiBold','Bold','ExtraBold'];
const text='Fractal Mono R r O o 0 ! ? {} ₹ © ® ™ Αβγ Привет Ắ';
const faces=styles.map((s,i)=>`@font-face{font-family:S${i};src:url('/fonts/webfonts/FractalMono-${s}.woff2') format('woff2')}`).join('');
const pageHTML=`<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Fractal Mono format check</title><link rel="icon" href="data:,"><link rel="stylesheet" href="/fractal-mono.css"><style>${faces}*{box-sizing:border-box}body{margin:24px;font-family:Arial,sans-serif}main{max-width:100%}.probe{font-size:28px;line-height:1.6;overflow-wrap:anywhere}.cell{display:inline-block}.label{font:16px Arial,sans-serif}</style><main><h1>Fractal Mono</h1><p id="variable" class="probe fractal-mono">${text}</p><p id="cells" class="fractal-mono probe">${['M','₹','©','?'].map(s=>`<span class="cell">${s}</span>`).join('')}</p>${styles.map((s,i)=>`<section><h2 class="label">${s}</h2><p id="s${i}" class="probe" style="font-family:S${i}">${text}</p></section>`).join('')}</main></html>`;
const server=createServer((req,res)=>{try{const path=decodeURIComponent(new URL(req.url,'http://localhost').pathname);if(path==='/'){res.writeHead(200,{'Content-Type':'text/html'});res.end(pageHTML);return}const target=resolve(root,'.'+path);if(!target.startsWith(root+sep))throw Error('outside project');const data=readFileSync(target);res.writeHead(200,{'Content-Type':{'.css':'text/css','.woff2':'font/woff2'}[extname(target)]??'application/octet-stream'});res.end(data)}catch{res.writeHead(404);res.end()}});
await new Promise(r=>server.listen(0,'127.0.0.1',r));
const browser=await chromium.launch({headless:true});const errors=[];const results={formats:[],viewports:[]};mkdirSync(resolve(root,'build/browser'),{recursive:true});
try{
 const page=await browser.newPage();page.on('pageerror',e=>errors.push(String(e)));page.on('console',m=>{if(m.type()==='error')errors.push(m.text())});
 for(const [name,width] of [['desktop',1280],['mobile',390]]){
  await page.setViewportSize({width,height:1000});await page.goto(`http://127.0.0.1:${server.address().port}/`);await page.evaluate(()=>document.fonts.ready);
  const session=await page.context().newCDPSession(page);await session.send('DOM.enable');await session.send('CSS.enable');const {root:document}=await session.send('DOM.getDocument');
  for(const selector of ['#variable',...styles.map((_,i)=>`#s${i}`)]){const {nodeId}=await session.send('DOM.querySelector',{nodeId:document.nodeId,selector});const {fonts}=await session.send('CSS.getPlatformFontsForNode',{nodeId});if(!fonts.length||fonts.some(f=>!f.isCustomFont))throw Error(`${selector}: fallback font`);if(name==='desktop')results.formats.push({selector,fonts:fonts.map(f=>f.familyName)})}
  await session.detach();
  const widths=await page.locator('.cell').evaluateAll(e=>e.map(x=>x.getBoundingClientRect().width));if(Math.max(...widths)-Math.min(...widths)>.0625)throw Error('cell widths differ');
  for(const weight of [100,400,800]){await page.locator('#variable').evaluate((e,w)=>e.style.fontVariationSettings=`"wght" ${w}, "opsz" 14`,weight);if(!await page.evaluate(()=>document.fonts.check('28px "Fractal Mono"')))throw Error('variable font unavailable')}
  const overflow=await page.evaluate(()=>document.documentElement.scrollWidth-document.documentElement.clientWidth);if(overflow)throw Error(`${name}: overflow ${overflow}`);
  await page.addScriptTag({content:readFileSync(createRequire(import.meta.url).resolve('axe-core/axe.min.js'),'utf8')});const accessibility=await page.evaluate(()=>axe.run());if(accessibility.violations.length)throw Error(JSON.stringify(accessibility.violations.map(v=>v.id)));
  results.viewports.push({name,overflow,cellWidths:widths,accessibilityViolations:0});await page.screenshot({path:resolve(root,`build/browser/${name}.png`),fullPage:true});
 }
 if(errors.length)throw Error(JSON.stringify(errors));results.errors=errors;writeFileSync(resolve(root,'build/browser/verification.json'),JSON.stringify(results,null,2));console.log('Variable and all eight CFF webfonts render without fallback, errors or overflow.');
}finally{await browser.close();await new Promise(r=>server.close(r))}
