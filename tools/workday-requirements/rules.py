import pandas as pd, pickle, sys
pos, ar, ser, meta = pickle.load(open(sys.argv[1], 'rb'))
names = sys.argv[2:]
cols = [c for c in ser.columns if c not in ('Programs of Study (Direct Academic Requirements)','Programs of Study (Direct + Hierarchy)')]
seen=set()
def show(n, depth=0):
    if n in seen: print('  '*depth+'(seen) '+n); return
    seen.add(n)
    rows = ser[ser['Student Eligibility Rule']==n]
    print('  '*depth + f'### {n!r}: {len(rows)} row(s)')
    for _, r in rows.iterrows():
        d = {c: (str(r[c])[:300].replace('\n\n',' | ')) for c in cols if pd.notna(r[c]) and r[c] not in (0, '', 'No') and c not in ('Student Eligibility Rule',)}
        for k,v in d.items(): print('  '*depth + f'   {k}: {v}')
        print('  '*depth+'   --')
    for _, r in rows.iterrows():
        sub = r['Student Eligibility Rules']
        if pd.notna(sub):
            for s in str(sub).split('\n'):
                if s.strip(): show(s.strip(), depth+1)
for n in names: show(n)
