import {bundle} from '@remotion/bundler';
import {renderStill,selectComposition,openBrowser} from '@remotion/renderer';
import fs from 'node:fs';
const url=await bundle({entryPoint:'src/index.tsx'});const browser=await openBrowser('chrome',{browserExecutable:'/usr/bin/chromium'});const composition=await selectComposition({serveUrl:url,id:'RydeResolve',puppeteerInstance:browser});const shots=JSON.parse(fs.readFileSync('src/timeline.json'));
for(const s of shots){for(const offset of (s.id==='other'?[40,200,300]:[40,Math.min(s.duration-30,200)])){const frame=s.fromFrame+offset;await renderStill({composition,serveUrl:url,output:`out/qa/${s.id}-${frame}.png`,frame,puppeteerInstance:browser});}console.log(s.id)}await browser.close({silent:true});
