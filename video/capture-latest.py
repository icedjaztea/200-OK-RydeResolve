import asyncio,json,pathlib,urllib.request
from playwright.async_api import async_playwright
R=pathlib.Path('/workspace/ryderesolve-video-v2/video');base='http://127.0.0.1:8001'
def api(path,data=None,key='change-reviewer-key',method=None):
 q=urllib.request.Request(base+path,data=json.dumps(data).encode() if data else None,headers={'X-Demo-Key':key,'Content-Type':'application/json'},method=method);return json.load(urllib.request.urlopen(q))
api('/cases/seed',method='POST');api('/cases',dict(case_id='DEMO-DRIVER-RMI',trip_id='DEMO-DISP-003',category='route_deviation',filed_by='driver',description='Synthetic route-change case requiring a timestamped notification reference.',dispute_amount=3.20,synthetic=True),key='change-driver-key')
async def connect(pg,role):
 await pg.goto('http://localhost:3001/'+role)
 for _ in range(2):
  b=pg.get_by_role('button',name='Connect',exact=True)
  if await b.count():await b.click();await pg.wait_for_timeout(500)
async def main():
 async with async_playwright() as p:
  b=await p.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox']);ctx=await b.new_context(viewport={'width':1920,'height':2000},device_scale_factor=2);pg=await ctx.new_page()
  await connect(pg,'reviewer');await pg.get_by_role('button').filter(has_text='DEMO-DRIVER-RMI').click();await pg.get_by_role('button',name='Ask a question',exact=True).click();await pg.locator('.clar-panel select').select_option('driver');await pg.locator('.clar-panel textarea').fill('Did you inform the rider before or at the route change? Please provide a timestamped in-app message or trip-call reference.');await pg.wait_for_timeout(300)
  card=pg.locator('.card').filter(has=pg.get_by_role('heading',name='Request More Information',exact=True));await card.screenshot(path=str(R/'public/textures/request-more-info.png'));print('Reviewer question card',await card.inner_text(),flush=True)
  await pg.get_by_role('button',name='Send Request',exact=True).click();await pg.wait_for_timeout(500);print('Waiting label',await pg.locator('body').inner_text(),flush=True)
  await connect(pg,'driver');await pg.get_by_role('button').filter(has_text='DEMO-DRIVER-RMI').first.click();await pg.wait_for_timeout(400);await pg.locator('.app-shell').screenshot(path=str(R/'public/textures/driver-requested-phone.png'));print('Driver request',await pg.locator('.app-action-card').inner_text(),flush=True);await b.close()
asyncio.run(main())
d=api('/cases/DEMO-DRIVER-RMI');(R/'out/request-more-info.json').write_text(json.dumps(d,indent=2))
