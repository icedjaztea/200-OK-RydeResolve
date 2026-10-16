import os
os.environ['OMP_NUM_THREADS']='2'
import json,pathlib,re,numpy as np,soundfile as sf,onnxruntime as ort
from kokoro_onnx import Kokoro
R=pathlib.Path('/workspace/ryderesolve-video-v2/video');(R/'public/audio').mkdir(exist_ok=True)
k=Kokoro('/workspace/ryderesolve-video/voice/kokoro.onnx','/workspace/ryderesolve-video/voice/voices.bin')
opt=ort.SessionOptions();opt.intra_op_num_threads=2;opt.inter_op_num_threads=1;k.sess=ort.InferenceSession('/workspace/ryderesolve-video/voice/kokoro.onnx',sess_options=opt,providers=['CPUExecutionProvider'])
scenes=json.loads((R/'scenes.json').read_text());cursor=0
for i,s in enumerate(scenes):
 segments=re.split(r'(?<=[.!?])\s+',s['narration']);samples=[np.zeros(12000,dtype=np.float32)];captions=[];t=.5
 for seg in segments:
  a,sr=k.create(seg,voice='af_heart',speed=1.25,lang='en-us');samples.extend([a,np.zeros(4000,dtype=np.float32)]);captions.append({'start':round(t*30),'end':round((t+len(a)/sr)*30),'text':seg});t+=len(a)/sr+4000/sr
 samples.append(np.zeros(18000,dtype=np.float32));audio=np.concatenate(samples);sf.write(str(R/'public/audio'/f'{s["id"]}.wav'),audio,24000)
 s.update(fromFrame=cursor,duration=int(np.ceil(len(audio)/24000*30)),captions=captions);cursor+=s['duration'];print(i,s['id'],round(s['duration']/30,1),flush=True)
 (R/'src/timeline.json').write_text(json.dumps(scenes,indent=2))
print('TOTAL',cursor/30,flush=True)
