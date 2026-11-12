import pandas as pd, pickle, sys
pd.set_option('display.width', 250); pd.set_option('display.max_colwidth', 140); pd.set_option('display.max_rows', 500)
pos, ar, ser, meta = pickle.load(open(sys.argv[1], 'rb'))
print(pos['Program of Study'].nunique(), 'programs;', pos['Code'].nunique(), 'codes')
print(pos['Eligibility Rule Type'].value_counts(dropna=False))
cs = pos[pos['Program of Study'].str.contains('Computer Science', na=False)]
print(cs['Program of Study'].unique())
b = pos[pos['Program of Study']=='Computer Science, BCS']
print(b[['Academic Requirement','Reference ID','Eligibility Rule Type','Student Eligibility Rule']].to_string())
