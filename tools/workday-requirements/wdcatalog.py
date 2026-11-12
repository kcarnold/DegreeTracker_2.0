"""Render a program as a catalog page using only Workday's structured rule fields."""
import pandas as pd, pickle, sys, re
pos, ar, ser, meta = pickle.load(open(sys.argv[1], 'rb'))
by = {n: g for n, g in ser.groupby('Student Eligibility Rule')}

def courses(cell):
    if not isinstance(cell, str): return []
    return [c.strip() for c in cell.split('\n\n') if c.strip() and not c.startswith('DUMMY')]

def grade(r):
    if pd.isna(r['Grade']): return ''
    op = {'greater than or equal to': 'at least', 'equal to': 'exactly'}.get(r['Operator'], r['Operator'])
    return f", grade {op} {r['Grade']}"

def leaf(r):
    t = r['Rule Type']; cs = courses(r['All Courses Including Courses from Smart Lists'])
    src = f"[{r['Smart Lists']}] ({len(cs)} courses)" if pd.notna(r['Smart Lists']) else '; '.join(cs) if len(cs) <= 6 else '; '.join(cs[:5]) + f'; … ({len(cs)} courses)'
    lim = f" — at most {int(r['Maximum Registrations Counted or Hours Allowed'])} {'registrations' if 'Repeat' in str(r['Class of Instance']) else 'hours'} from {r['Course Set for Student Eligibility Rule Limit']}" if pd.notna(r['Class of Instance']) else ''
    if t == 'Course Requirement':
        n = int(r['Number of Courses'] or 0)
        q = 'All of' if r['Selector'] == 'all' else f'Any {n} of' if n > 1 else 'One of'
        if len(cs) == 1 and q in ('All of', 'One of'): return f"{cs[0]}{grade(r)}{lim}"
        return f"{q}: {src}{grade(r)}{lim}"
    if t == 'Hour Requirement':
        return f"{int(r['Hours'])} hours from: {src}{grade(r)}{lim}"
    if t == 'Grade Requirement':
        return str(r['Eligibility Rule Meaning'])
    return f"[{t}] {r['Eligibility Rule Meaning']}"

def render(name, depth=0):
    g = by[name]; first = g.iloc[0]
    if first['Rule Type'] != 'Combination':
        return leaf(first) + ''.join(f"; at most {int(x['Maximum Registrations Counted or Hours Allowed'])} from {x['Course Set for Student Eligibility Rule Limit']}" for _, x in g.iloc[1:].iterrows())
    parts = []
    for i, (_, line) in enumerate(g.sort_values('Order').iterrows()):
        subs = [render(s.strip(), depth + 1) for s in str(line['Student Eligibility Rules']).split('\n') if s.strip()]
        n = int(line['Number of Rules'] or 0)  # for 'any': how many sub-rules must be met
        sel = 'all of' if line['Selector for Combination Eligibility Rule'] == 'all' else f'any {n} of' if n > 1 else 'any of'
        body = subs[0] if len(subs) == 1 else sel + ' {' + ' | '.join(subs) + '}'
        op = '' if i == 0 else f" {line['And/Or'].upper()} "
        parts.append(op + str(line['Open Parenthesis'] if pd.notna(line['Open Parenthesis']) else '') + body + str(line['Close Parenthesis'] if pd.notna(line['Close Parenthesis']) else ''))
    return ''.join(parts)

for prog in sys.argv[2:]:
    rows = pos[pos['Program of Study'] == prog].dropna(subset=['Student Eligibility Rule'])
    print(f"\n{'=' * 70}\n{prog}   ({rows['Code'].iloc[0]}, {rows['Owning Academic Unit'].iloc[0]})\n{'=' * 70}")
    for _, q in rows.iterrows():
        rule = q['Student Eligibility Rule']; g = by[rule].iloc[0]
        text = render(rule)
        print(f"• {text[:400]}{' …' if len(text) > 400 else ''}")
        if g['Use Custom Meaning'] == 'Yes' and pd.notna(g['Custom Eligibility Rule Meaning']):
            print(f"    “{' '.join(str(g['Custom Eligibility Rule Meaning']).split())[:300]}”")
