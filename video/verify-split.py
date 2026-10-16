from pathlib import Path
import json,subprocess
from PIL import Image,ImageDraw
r=Path(__file__).resolve().parent;p=r/'out/RydeResolve-Split-View-Walkthrough.mp4'
d=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-show_chapters','-of','json',str(p)]))
v=next(s for s in d['streams'] if s['codec_type']=='video');assert (v['width'],v['height'],v['r_frame_rate'],int(v['nb_frames']))==(1920,1080,'30/1',7661);assert len(d['chapters'])==19;assert any(s['codec_type']=='audio' for s in d['streams']);assert any(s['codec_type']=='subtitle' for s in d['streams'])
(r/'out/split-media-verification.json').write_text(json.dumps(d,indent=2)+'\n')
ss=json.loads((r/'src/timeline.json').read_text());frames=[]
for s in ss:frames.extend([s['fromFrame']+15,s['fromFrame']+min(130,s['duration']-60),s['fromFrame']+s['duration']-40])
frames+= [1244,2081,2742,3002,3343,4897,4997,5190,5333,5671];frames=sorted(set(frames));dest=r/'out/split-final-frames';dest.mkdir(exist_ok=True)
for f in frames:subprocess.run(['ffmpeg','-v','error','-ss',str(f/30),'-i',str(p),'-frames:v','1','-y',str(dest/f'frame-{f}.png')],check=True)
im=Image.new('RGB',(1440,((len(frames)+2)//3)*292),'#eee');dr=ImageDraw.Draw(im)
for i,f in enumerate(frames):
 a=Image.open(dest/f'frame-{f}.png');a.thumbnail((480,270));x=i%3*480;y=i//3*292;im.paste(a,(x,y));dr.text((x+8,y+272),f'frame {f}',fill='black')
im.save(r/'out/split-contact.jpg',quality=90)
preview=Image.new('RGB',(1440,584),'#eee');dr=ImageDraw.Draw(preview)
for i,f in enumerate([1244,2081,3002,3343,5190,5671]):
 a=Image.open(dest/f'frame-{f}.png');a.thumbnail((480,270));x=i%3*480;y=i//3*292;preview.paste(a,(x,y));dr.text((x+8,y+272),f'frame {f}',fill='black')
preview.save(r/'out/split-preview.jpg',quality=90)
print('FRAMES_READY',flush=True)
with (r/'out/split-decode-check.txt').open('w') as o:subprocess.run(['ffmpeg','-v','warning','-i',str(p),'-f','null','-'],stderr=o,check=True)
with (r/'out/split-audio-analysis.txt').open('w') as o:subprocess.run(['ffmpeg','-hide_banner','-i',str(p),'-af','loudnorm=I=-16:TP=-1.6:LRA=9:print_format=json','-f','null','-'],stdout=o,stderr=subprocess.STDOUT,check=True)
print('SPLIT_VERIFICATION_COMPLETE',flush=True)
