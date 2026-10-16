import json,pathlib
r=pathlib.Path(__file__).parent
ss=json.loads((r/'src/timeline.json').read_text())
def tc(f):
 m=round(f/30*1000);h,m=divmod(m,3600000);mi,m=divmod(m,60000);s,ms=divmod(m,1000);return f'{h:02}:{mi:02}:{s:02},{ms:03}'
cues=[];chap=[';FFMETADATA1']
for s in ss:
 chap+=['[CHAPTER]','TIMEBASE=1/30',f"START={s['fromFrame']}",f"END={s['fromFrame']+s['duration']}",f"title={s['title']}"]
 for c in s['captions']:
  w=c['text'].split();chunks=[w[i:i+5] for i in range(0,len(w),5)];n=0
  for chunk in chunks:
   a=c['start']+(c['end']-c['start'])*n/len(w);n+=len(chunk);b=c['start']+(c['end']-c['start'])*n/len(w)
   cues.append(f'{len(cues)+1}\n{tc(s["fromFrame"]+a)} --> {tc(s["fromFrame"]+b)}\n'+ ' '.join(chunk)+'\n')
(r/'out/ryderesolve-captions.srt').write_text('\n'.join(cues));(r/'out/chapters.ffmeta').write_text('\n'.join(chap)+'\n')
