from pathlib import Path
import json, zipfile
from PIL import Image,ImageDraw
r=Path(__file__).parent
ss=json.loads((r/'src/timeline.json').read_text())
(r/'out/asset-manifest.json').write_text(json.dumps({'developer_baseline':'46d17cf1b2e02ed8d4b66d6aa267ea720443ea09','duration_frames':7661,'fps':30,'scenes':[{'id':s['id'],'fromFrame':s['fromFrame'],'duration':s['duration'],'image':s.get('image')} for s in ss]},indent=2)+'\n')
frames=[899,1244,2468,4997,5190,6574]
im=Image.new('RGB',(1440,584),'#eee');d=ImageDraw.Draw(im)
for i,f in enumerate(frames):
 p=r/'out/final-frames'/f'frame-{f}.png'
 if not p.exists():
  import subprocess
  subprocess.run(['ffmpeg','-v','error','-ss',str(f/30),'-i',str(r/'out/RydeResolve-Submission-Walkthrough-v2.mp4'),'-frames:v','1','-y',str(p)],check=True)
 a=Image.open(p);a.thumbnail((480,270));x=i%3*480;y=i//3*292;im.paste(a,(x,y));d.text((x+8,y+272),f'frame {f}',fill='black')
im.save(r/'out/preview.jpg',quality=90)
proof=['asset-manifest.json','backend-tests.txt','frontend-tests.txt','correction-checks.txt','decode-check.txt','driver-request-check.txt','fare.json','route.json','safety.json','other.json','other-refund-blocked.json','other-reclassified.json','request-more-info.json','parity.log','parity-latest.log','typescript-check.txt','selected-shot-reference.json','media-verification.json','final-audio-analysis.txt','independent-review.md','chapters.ffmeta','ryderesolve-captions.srt','preview.jpg','final-contact.jpg']
for name in proof:
 p=r/'out'/name
 if p.suffix not in ['.jpg','.png']:
  p.write_text('\n'.join(line.rstrip() for line in p.read_text().splitlines()).rstrip()+'\n')
files=[]
for name in ['src','public']:
 files+=list((r/name).rglob('*'))
files += [p for p in r.iterdir() if p.is_file() and p.suffix in ['.md','.json','.txt','.ts','.sh','.py','.mjs'] and p.name!='package-project.py']
files += [r/'out'/n for n in proof]
with zipfile.ZipFile(r/'out/RydeResolve-editable-project-v2.zip','w',zipfile.ZIP_DEFLATED) as z:
 for p in files:
  if p.is_file():z.write(p,'RydeResolve-video-v2/'+str(p.relative_to(r)))
(r/'out/retained-proof-list.txt').write_text('\n'.join(proof)+'\n')
