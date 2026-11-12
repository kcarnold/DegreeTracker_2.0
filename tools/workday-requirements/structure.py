import pandas as pd, pickle, sys, re
pd.set_option('display.width', 250); pd.set_option('display.max_colwidth', 200); pd.set_option('display.max_rows', 500)
pos, ar, ser, meta = pickle.load(open(sys.argv[1], 'rb'))
g = ser.groupby('Reference ID')
multi = g.size()[g.size()>1]
print('multi-row rules', len(multi), 'max rows', multi.max())
kinds = {}
for ref, rows in g:
    if len(rows) < 2: continue
    hasc = rows['Order'].notna().sum(); hasl = rows['Class of Instance'].notna().sum()
    k = ('combo' if hasc else '') + ('+limit' if hasl else '')
    kinds[k] = kinds.get(k, 0)+1
    if hasc and rows['Order'].dropna().duplicated().any(): print('dup order in', ref)
    if hasc and hasl: print('combo AND limit:', ref)
print(kinds)
# limit-only multi rows: are other fields identical across rows (i.e., one row per limit line)?
# number of rules semantics with parens
pr = ser[ser['Open Parenthesis'].notna() | ser['Close Parenthesis'].notna()]['Reference ID'].unique()
for ref in pr[:3]:
    print(ser[ser['Reference ID']==ref][['Student Eligibility Rule','Order','Open Parenthesis','Number of Rules','And/Or','Selector for Combination Eligibility Rule','Student Eligibility Rules','Close Parenthesis']].to_string())
# sub-rule names: count vs Number of Rules
c = ser[ser['Order'].notna()].copy()
c['n_listed'] = c['Student Eligibility Rules'].fillna('').apply(lambda s: len([x for x in s.split('\n') if x.strip()]))
bad = c[c['n_listed'] != c['Number of Rules']]
print('lines where listed sub-rules != Number of Rules:', len(bad), 'of', len(c))
print(bad[['Student Eligibility Rule','Number of Rules','n_listed','Student Eligibility Rules']].head(8).to_string())
# core in ser?
core = ser[ser['Student Eligibility Rule'].str.contains(r'Core|Knowledge and Understanding|Diversity|Global Regions|Rhetoric', na=False)]
print('core-ish rules:', core['Student Eligibility Rule'].nunique()); print(core['Student Eligibility Rule'].drop_duplicates().head(30).to_string())
