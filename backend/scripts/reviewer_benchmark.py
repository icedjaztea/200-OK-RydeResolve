"""Use manual measurements, not fictional Ryde workload metrics."""
import csv,sys,statistics
from pathlib import Path
path=Path(sys.argv[1]) if len(sys.argv)>1 else Path('fixtures/evaluation/reviewer_time_template.csv')
rows=list(csv.DictReader(path.open()))
pairs=[]
for row in rows:
    if row['manual_seconds'].strip() and row['assisted_seconds'].strip():
        pairs.append((float(row['manual_seconds']),float(row['assisted_seconds'])))
if len(pairs)<3:
    print('Need at least 3 real paired observations before reporting reviewer-time metrics.')
    raise SystemExit(1)
a=sum(x[0] for x in pairs);b=sum(x[1] for x in pairs)
print(f'Paired cases: {len(pairs)}')
print(f'Mean manual: {statistics.mean(x[0] for x in pairs):.1f}s')
print(f'Mean assisted: {statistics.mean(x[1] for x in pairs):.1f}s')
print(f'Observed time saving: {(a-b)/a*100:.1f}% (small convenience sample; do not extrapolate as Ryde baseline)')
