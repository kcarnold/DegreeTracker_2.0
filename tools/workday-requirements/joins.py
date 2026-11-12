import pandas as pd, pickle, sys
pd.set_option('display.width', 250); pd.set_option('display.max_colwidth', 120); pd.set_option('display.max_rows', 500)
pos, ar, ser, meta = pickle.load(open(sys.argv[1], 'rb'))
print('Last Entry Date non-null:', pos['Last Entry Date'].notna().sum(), pos['Last Entry Date'].dropna().unique()[:5])
print('programs w/ Core in name:', [p for p in pos['Program of Study'].unique() if 'ore' in p and 'Core' in p][:20])
core_like = pos[pos['Academic Requirement'].str.contains('Core|Knowledge and Understanding|Foundations', na=False)]
print('core-like requirement rows:', len(core_like)); print(core_like[['Program of Study','Academic Requirement']].head(10).to_string())
# key uniqueness
for name, d, k in [('pos ref', pos, 'Reference ID'), ('ar req ref', ar, 'Requirement Ref ID'), ('ar eligref', ar, 'Eligibility Rule Ref ID'), ('ser ref', ser, 'Reference ID'), ('ser name', ser, 'Student Eligibility Rule'), ('ar name', ar, 'Academic Requirement')]:
    s = d[k].dropna().astype(str)
    print(f'{name}: {len(s)} rows, {s.nunique()} unique')
# does ser have multiple rows per rule (combination lines)?
print(ser['Rule Type'].value_counts(dropna=False))
# pos -> ar by ref id
pr = set(pos['Reference ID'].astype(str)); arr = set(ar['Requirement Ref ID'].astype(str))
print('pos refs not in ar:', len(pr - arr), list(pr-arr)[:10])
# pos rule names vs ser names
pn = set(pos['Student Eligibility Rule'].dropna()); sn = set(ser['Student Eligibility Rule'].dropna())
print('pos rule names not in ser:', len(pn - sn), list(pn - sn)[:10])
# ar elig ref -> ser ref
ae = set(ar['Eligibility Rule Ref ID'].dropna().astype(str)); se = set(ser['Reference ID'].dropna().astype(str))
print('ar elig refs not in ser:', len(ae - se))
dup = ser['Student Eligibility Rule'].dropna()
dupnames = ser.dropna(subset=['Reference ID']).groupby('Student Eligibility Rule')['Reference ID'].nunique()
print('rule names with >1 ref id:', (dupnames>1).sum()); print(dupnames[dupnames>1].head(15))
