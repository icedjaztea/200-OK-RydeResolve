from pathlib import Path
import zipfile
r=Path(__file__).resolve().parent
proof=['split-parity.log','split-media-verification.json','split-audio-analysis.txt','split-decode-check.txt','split-independent-review.md','split-contact.jpg','split-preview.jpg','ryderesolve-captions.srt','chapters.ffmeta','backend-tests.txt','frontend-tests.txt','selected-shot-reference.json','fare.json','other.json','other-reclassified.json','request-more-info.json']
for n in proof:
 p=r/'out'/n
 if p.suffix not in ['.jpg','.png']:p.write_text('\n'.join(x.rstrip() for x in p.read_text().splitlines()).rstrip()+'\n')
files=[]
for folder in ['src','public']:files.extend((r/folder).rglob('*'))
files.extend(p for p in r.iterdir() if p.is_file() and p.suffix in ['.md','.json','.txt','.ts','.sh','.py','.mjs'])
files.extend(r/'out'/n for n in proof)
with zipfile.ZipFile(r/'out/RydeResolve-Split-View-Editable-Project.zip','w',zipfile.ZIP_DEFLATED) as z:
 for p in files:
  if p.is_file():z.write(p,'RydeResolve-split-view/'+str(p.relative_to(r)))
