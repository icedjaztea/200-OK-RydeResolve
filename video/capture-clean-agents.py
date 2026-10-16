import asyncio,pathlib
from playwright.async_api import async_playwright
async def m():
 async with async_playwright() as p:
  b=await p.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox']);pg=await b.new_page(viewport={'width':1920,'height':1080},device_scale_factor=2);await pg.goto('http://localhost:3001/reviewer');await pg.get_by_label('Demo passcode').fill('change-reviewer-key');await pg.get_by_role('button',name='Connect',exact=True).click();await pg.get_by_role('button').filter(has_text='DISP-003').click();await pg.get_by_role('tab').filter(has_text='Agent Findings').click();await pg.wait_for_timeout(500);await pg.screenshot(path='public/textures/fare-agents.png',full_page=True);await b.close()
asyncio.run(m())
