import pandas as pd, warnings, pickle, sys
warnings.filterwarnings('ignore')
f = sys.argv[1]
pos = pd.read_excel(f, sheet_name='Program of Study Requirements', header=1)
ar = pd.read_excel(f, sheet_name='Academic Requirements', header=0)
ser = pd.read_excel(f, sheet_name='Student Eligibility Rules', header=1)
meta = pd.read_excel(f, sheet_name='meta')
pickle.dump((pos, ar, ser, meta), open(sys.argv[2], 'wb'))
for n, d in [('pos', pos), ('ar', ar), ('ser', ser)]:
    print(n, d.shape); print(list(d.columns))
