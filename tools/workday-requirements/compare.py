import pandas as pd, pickle, sys, collections
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from resolve import R, name_codes
pos, ar, ser, meta = pickle.load(open(sys.argv[1], 'rb'))
r = R(ser)
reqs = pos.dropna(subset=['Reference ID']).drop_duplicates('Reference ID')
rows = []
for _, q in reqs.iterrows():
    rc = r.courses(q['Student Eligibility Rule']) - {'DUMMY 100','DUMMY 101'}
    nc, ranges = name_codes(q['Academic Requirement'])
    inrange = lambda c: any(c.split()[0]==s and c.split()[1][:3].isdigit() and lo <= int(c.split()[1][:3]) <= hi for s,lo,hi in ranges)
    extra = {c for c in rc - nc if not inrange(c)}
    missing = nc - rc
    rows.append(dict(ref=q['Reference ID'], name=q['Academic Requirement'], rule=q['Student Eligibility Rule'], n_rule=len(rc), n_name=len(nc), extra=sorted(extra), missing=sorted(missing), ranges=ranges))
df = pd.DataFrame(rows)
df.to_pickle(sys.argv[2] if len(sys.argv) > 2 else sys.argv[1].replace('.pkl', '-compare.pkl'))
has = df[df.n_name>0]
print('distinct requirements:', len(df), '; with course codes in name:', len(has))
print('  exact match:', ((has.extra.str.len()==0)&(has.missing.str.len()==0)).sum())
print('  rule accepts courses not in name:', (has.extra.str.len()>0).sum())
print('  name lists courses rule lacks:', (has.missing.str.len()>0).sum())
ec = collections.Counter(c for e in has.extra for c in e); print('most common extras:', ec.most_common(25))
mc = collections.Counter(c for e in has.missing for c in e); print('most common missing:', mc.most_common(25))
