import os
os.environ['OMP_NUM_THREADS']='2'
import pathlib,json,re,numpy as np,soundfile as sf,onnxruntime as ort,subprocess
from kokoro_onnx import Kokoro
R=pathlib.Path('/workspace/ryderesolve-video-v2/video');model='/workspace/ryderesolve-video/voice/kokoro.onnx';voices='/workspace/ryderesolve-video/voice/voices.bin';k=Kokoro(model,voices);opt=ort.SessionOptions();opt.intra_op_num_threads=2;opt.inter_op_num_threads=1;k.sess=ort.InferenceSession(model,sess_options=opt,providers=['CPUExecutionProvider'])
d=json.load(open(R/'src/timeline.json'))
for s in d:
 if s['id'] not in ['driver','measurements']:continue
 if s['id']=='driver':
  s['title']='Request evidence. Hear the response.';s['sub']='New: reviewer question → driver clarification';s['image']='driver-requested-card';s['phoneFrom']=0;s['phoneTo']=0;s['narration']='A reviewer can now ask either party for more information. The driver is asked for a timestamped message or call reference. Replies remain unverified until supported by evidence.'
 else:s['narration']=s['narration'].replace('three hundred and twenty four','three hundred and forty six')
 samples=[np.zeros(12000,dtype=np.float32)];captions=[];t=.5
 for seg in re.split(r'(?<=[.!?])\s+',s['narration']):
  a,sr=k.create(seg,voice='af_heart',speed=1.25,lang='en-us');samples.extend([a,np.zeros(4000,dtype=np.float32)]);captions.append({'start':round(t*30),'end':round((t+len(a)/sr)*30),'text':seg});t+=len(a)/sr+4000/sr
 samples.append(np.zeros(18000,dtype=np.float32));a=np.concatenate(samples);raw=R/'out'/f'{s["id"]}-new-raw.wav';sf.write(raw,a,24000);target=s['duration']/30;ratio=len(a)/24000/target
 subprocess.run(['ffmpeg','-v','error','-i',str(raw),'-af',f'atempo={ratio},apad,atrim=duration={target}','-y',str(R/'public/audio'/f'{s["id"]}.wav')],check=True)
 for c in captions:c['start']=round(c['start']/ratio);c['end']=min(s['duration'],round(c['end']/ratio))
 s['captions']=captions;print(s['id'],'fit ratio',ratio,flush=True)
(R/'src/timeline.json').write_text(json.dumps(d,indent=2));(R/'script.txt').write_text('\n\n'.join(s['title']+'\n'+s['narration'] for s in d))
