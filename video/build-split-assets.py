from pathlib import Path
from PIL import Image
r=Path(__file__).resolve().parent
# Pixel-only crops of retained 2x browser captures; no page contents are altered.
crops={'split-fare-overview':('fare-overview',(548,152,1668,1044)), 'split-fare-evidence':('fare-evidence',(548,540,1668,1460)), 'split-fare-agents':('fare-agents',(548,540,1668,1570)), 'split-other-review':('other-review',(548,152,1668,1430)), 'split-other-reclassified':('other-reclassified',(548,152,1668,1160))}
for out,(src,box) in crops.items():
 im=Image.open(r/'public/textures'/f'{src}.png');im.crop(tuple(int(v*2) for v in box)).save(r/'public/textures'/f'{out}.png')
im=Image.open(r/'public/textures/rider-outcome-phone.png')
for name,box in {'split-rider-decision':(0,140,480,338),'split-rider-refund':(0,910,480,990),'split-rider-progress':(0,1200,480,1690)}.items():
 im.crop(tuple(int(v*2) for v in box)).save(r/'public/textures'/f'{name}.png')
