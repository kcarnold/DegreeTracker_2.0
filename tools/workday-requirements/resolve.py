import pandas as pd, pickle, re
CODE = re.compile(r'\b([A-Z]{2,5})\s*(\d{3}[A-Z]?|W\d{2})\b')
def leaf_codes(cell):
    out = set()
    if not isinstance(cell, str): return out
    for item in cell.split('\n\n'):
        head = item.split(' - ')[0]
        for part in head.split('/'):
            m = CODE.search(part.strip())
            if m: out.add(f'{m.group(1)} {m.group(2)}')
    return out
def name_codes(text):
    """Codes mentioned in catalog-style text: 'CS 300, 312; ENGR 304' and ranges 'BIOL 311-364'."""
    codes, ranges = set(), []
    if not isinstance(text, str): return codes, ranges
    subj = None
    for m in re.finditer(r'\b([A-Z]{2,5})\b(?=\s*\d|\s*W\d)|(\d{3})\s*[-–]\s*(\d{3})|\b(\d{3}[A-Z]?|W\d{2})\b', text):
        if m.group(1): subj = m.group(1)
        elif m.group(2) and subj: ranges.append((subj, int(m.group(2)), int(m.group(3))))
        elif m.group(4) and subj: codes.add(f'{subj} {m.group(4)}')
    return codes, ranges
class R:
    def __init__(self, ser):
        self.by = {n: g for n, g in ser.groupby('Student Eligibility Rule')}
    def courses(self, name, seen=None):
        seen = seen or set()
        if name in seen or name not in self.by: return set()
        seen.add(name); g = self.by[name]; out = set()
        out |= leaf_codes(g['All Courses Including Courses from Smart Lists'].iloc[0])
        for s in g['Student Eligibility Rules'].dropna():
            for sub in s.split('\n'):
                if sub.strip(): out |= self.courses(sub.strip(), seen)
        return out
    def types(self, name, seen=None):
        seen = seen or set()
        if name in seen or name not in self.by: return set()
        seen.add(name); g = self.by[name]; out = {g['Rule Type'].iloc[0]}
        for s in g['Student Eligibility Rules'].dropna():
            for sub in s.split('\n'):
                if sub.strip(): out |= self.types(sub.strip(), seen)
        return out
