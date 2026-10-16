import asyncio,pathlib,json,urllib.request
from playwright.async_api import async_playwright
R=pathlib.Path('/workspace/ryderesolve-video-v2/video')
async def m():
 async with async_playwright() as p:
  b=await p.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox']);pg=await b.new_page(viewport={'width':1920,'height':2000},device_scale_factor=2);await pg.goto('http://localhost:3001/driver');await pg.get_by_label('Demo identity').select_option('change-driver-key');await pg.get_by_role('button',name='Connect',exact=True).click();await pg.get_by_role('button').filter(has_text='DEMO-DRIVER-RMI').first.click();await pg.wait_for_timeout(500);card=pg.locator('.app-action-card');await card.screenshot(path=str(R/'public/textures/driver-requested-card.png'));(R/'out/driver-request-check.txt').write_text(await card.inner_text());await b.close()
asyncio.run(m())
q=urllib.request.Request('http://127.0.0.1:8001/cases/DEMO-DRIVER-RMI',headers={'X-Demo-Key':'change-reviewer-key'});d=json.load(urllib.request.urlopen(q));(R/'out/request-more-info.json').write_text(json.dumps(d,indent=2))
