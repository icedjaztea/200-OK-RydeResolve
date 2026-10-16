import asyncio,json,pathlib,urllib.request
from playwright.async_api import async_playwright
R=pathlib.Path('/workspace/ryderesolve-video-v2/video');OUT=R/'public/textures'
# Freeze synthetic trip data before browser capture; no random/live trip history.
trips=[]
for i,(tid,pick,drop,fare) in enumerate([('DEMO-DISP-003','Orchard Road','Marina Bay',16.50),('TRIP-DEMO-002','Bishan','Paya Lebar',18.20),('TRIP-DEMO-003','Novena','Clementi',22.00)]):
 trips.append(dict(trip_id=tid,date='2026-10-16',time=['09:30','08:15','07:40'][i],pickup_location=pick,dropoff_location=drop,pickup_lat=1.3048,pickup_lng=103.8318,dropoff_lat=1.2834,dropoff_lng=103.8607,distance_km=7.2+i*2,duration_min=18+i*5,fare=fare,currency='SGD',driver_name='Demo Driver A',vehicle_info='Demo vehicle',driver_rating=4.8,rider_name='Demo Rider A',rider_rating=4.8,status='completed',payment_method='Demo card'))
store={'change-rider-key':trips,'change-driver-key':trips};(R/'demo-trips.json').write_text(json.dumps(trips,indent=2))
layouts={}
async def main():
 async with async_playwright() as p:
  b=await p.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox']);ctx=await b.new_context(viewport={'width':1920,'height':1080},device_scale_factor=2)
  await ctx.add_init_script('if(location.hostname===\'localhost\')localStorage.setItem("ryderesolve_trips_v1",'+json.dumps(json.dumps(store))+');')
  page=await ctx.new_page()
  async def snap(name,phone=False):
   await page.evaluate('document.fonts.ready');await page.wait_for_timeout(650);await page.evaluate('window.scrollTo(0,0)')
   await page.screenshot(path=str(OUT/(name+'.png')),full_page=True)
   layouts[name]={'pageH':await page.locator('body').evaluate('(e)=>e.scrollHeight'),'elements':await page.locator('.card,.rule-detail,.agent-step,.trip-card,.app-form,.app-case-card').evaluate_all('(es)=>es.map(e=>{let r=e.getBoundingClientRect();return {cls:e.className,x:r.x,y:r.y+scrollY,w:r.width,h:r.height}})')}
   if phone:await page.locator('.app-shell').screenshot(path=str(OUT/(name+'-phone.png')))
   print(name,flush=True)
  await page.goto('http://localhost:3001/driver');await page.get_by_label('Demo passcode').fill('change-driver-key');await page.get_by_role('button',name='Connect',exact=True).click();await page.wait_for_timeout(400);await page.get_by_role('button',name='Trips',exact=True).click();await page.get_by_role('button').filter(has_text='DEMO-DISP-003').click();await snap('driver-trip',True)
  await page.get_by_role('button',name='Disputes',exact=True).click();await page.get_by_role('button').filter(has_text='DEMO-DRIVER-CLARIFY').first.click();await snap('driver-clarification',True)
  await page.goto('http://localhost:3001/rider');await page.get_by_label('Demo passcode').fill('change-rider-key');await page.get_by_role('button',name='Connect',exact=True).click();await page.get_by_role('button').filter(has_text='DISP-003').click();await snap('rider-outcome',True)
  await page.goto('http://localhost:3001/monitor');await page.locator('input').fill('change-reviewer-key');await page.get_by_role('button',name='Refresh cases',exact=True).click();await page.locator('select').select_option('DISP-003');await page.wait_for_timeout(300);await snap('monitor')
  for i in range(1,10):
   await page.get_by_role('button').filter(has_text='Step').click();await page.wait_for_timeout(80)
   if i in [3,6,9]:await snap('monitor-'+str(i))
  (OUT/'layout.json').write_text(json.dumps(layouts,indent=2));await b.close()
asyncio.run(main())
