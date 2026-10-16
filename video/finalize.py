import os,time,pathlib,subprocess,json
from PIL import Image,ImageDraw
R=pathlib.Path(__file__).resolve().parent
if not (R/'out/ryderesolve-walkthrough.mp4').exists():raise RuntimeError('Render did not produce MP4')
subprocess.run(['bash','finish.sh'],cwd=R,check=True)
p=R/'out/RydeResolve-Submission-Walkthrough-v2.mp4'
r=subprocess.run(['ffprobe','-v','error','-show_streams','-show_format','-show_chapters','-of','json',str(p)],capture_output=True,text=True,check=True);(R/'out/media-verification.json').write_text(r.stdout)
d=json.loads(r.stdout);v=next(x for x in d['streams'] if x['codec_type']=='video');assert(v['width'],v['height'],v['r_frame_rate'],int(v['nb_frames']))==(1920,1080,'30/1',7661);assert len(d['chapters'])==19
ss=json.loads((R/'src/timeline.json').read_text());frames=[]
for s in ss:frames.extend([s['fromFrame']+40,s['fromFrame']+min(200,s['duration']-30)])
frames.extend([4997,5190]);frames=sorted(set(frames));(R/'out/final-frames').mkdir(exist_ok=True)
for f in frames:subprocess.run(['ffmpeg','-v','error','-ss',str(f/30),'-i',str(p),'-frames:v','1','-y',str(R/'out/final-frames'/f'frame-{f}.png')],check=True)
contact=Image.new('RGB',(1440,((len(frames)+2)//3)*292),'#eee');draw=ImageDraw.Draw(contact)
for i,f in enumerate(frames):
 im=Image.open(R/'out/final-frames'/f'frame-{f}.png');im.thumbnail((480,270));x=i%3*480;y=i//3*292;contact.paste(im,(x,y));draw.text((x+8,y+272),f'frame-{f}',fill='black')
contact.save(R/'out/final-contact.jpg',quality=90)
print('FINAL_READY',str(p),round(p.stat().st_size/1024/1024,1),'MB',flush=True)
subprocess.run(['ffmpeg','-v','warning','-i',str(p),'-f','null','-'],stderr=open(R/'out/decode-check.txt','w'),check=True)
subprocess.run(['ffmpeg','-hide_banner','-i',str(p),'-af','loudnorm=I=-16:TP=-1.5:LRA=9:print_format=json','-f','null','-'],stdout=open(R/'out/final-audio-analysis.txt','w'),stderr=subprocess.STDOUT,check=True)
print('DECODE_AND_AUDIO_CHECK_DONE',flush=True)
