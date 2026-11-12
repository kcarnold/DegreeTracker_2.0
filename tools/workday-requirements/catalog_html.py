"""Render programs of study as an HTML "catalog" built only from Workday's rule data.

    python3 catalog_html.py dfs.pkl out.html "bcs=Computer Science, BCS" \
        "nursing=Pre-nursing+Nursing, BSN" "biology=Biology, BS"

Each argument after the output path is anchor=Program[+Program...]; programs joined
with + are shown together (the catalog's Nursing page is two Workday programs).
dfs.pkl comes from load.py. Requirements are listed in Workday's order; each rule is
rendered from its structured fields (selector, counts, hours, grade, limits,
combination lines), not from its name. NOTES holds what we found comparing a
program with its catalog page by hand; they are not derived from the data.
"""
import html, pickle, re, sys
import pandas as pd

NOTES = {
    'bcs': 'Compared with the 2026–27 catalog page (via the upstream bcs-25.json): same courses, '
           'except that Workday also accepts MATH 312 (cross-listed with CS 312) and PHYS 235L.',
    'nursing': 'The catalog shows one Nursing, BSN page; Workday splits it into Pre-nursing and Nursing, BSN, '
               'which together list exactly the catalog’s 32 courses. Workday’s CHEM 160 requirement leaves out '
               'CHEM 160L, although the catalog requires a C in corequisite labs too. The catalog’s repeat and '
               'withdrawal limits, B minimum for transfer courses, and IDIS 108 waiver are not in Workday’s rules.',
    'biology': 'Not compared with the catalog page (we have no saved copy).',
}

e = lambda s: html.escape(str(s), quote=True)


def courses(cell):
    items = [c.strip() for c in cell.split('\n\n') if c.strip()] if isinstance(cell, str) else []
    real = [c for c in items if not c.startswith('DUMMY')]
    return real, len(items) - len(real)


def course_html(item):
    code, _, title = item.partition(' - ')
    return f'<li><span class="code">{e(code.strip())}</span> <span class="title">{e(title.strip())}</span></li>'


def course_list(items, smart=None, inline_max=8):
    if not items:
        return ''
    lis = ''.join(course_html(c) for c in items)
    label = f'Smart list: {e(smart)} · ' if isinstance(smart, str) else ''
    if len(items) <= inline_max and not isinstance(smart, str):
        return f'<ul class="courses">{lis}</ul>'
    preview = ', '.join(e(c.split(' - ')[0].strip()) for c in items[:4])
    return (f'<details class="courses-more"><summary>{label}{len(items)} courses '
            f'<span class="muted">({preview}, …)</span></summary><ul class="courses">{lis}</ul></details>')


def grade_chip(r):
    if pd.isna(r['Grade']):
        return ''
    scheme = re.search(r'\(Calvin ([A-Za-z]+) Grading Scheme\)', str(r['Eligibility Rule Meaning']))
    op = {'greater than or equal to': '≥', 'equal to': '='}.get(r['Operator'], str(r['Operator']))
    note = ' (transfer scale)' if scheme and scheme.group(1) == 'Transfer' else ''
    return f'<span class="chip grade">grade {op} {e(r["Grade"])}{note}</span>'


def limit_html(rows):
    out = []
    for _, r in rows.iterrows():
        if pd.isna(r['Class of Instance']):
            continue
        n = int(r['Maximum Registrations Counted or Hours Allowed'])
        items, _ = courses(r['Course Set for Student Eligibility Rule Limit'])
        what = f'counts at most {n} registrations of' if 'Repeat' in r['Class of Instance'] else f'at most {n} hours from'
        codes = ', '.join(c.split(' - ')[0].strip() for c in items)
        if len(items) > 12:
            codes = f'{len(items)} courses ({", ".join(c.split(" - ")[0].strip() for c in items[:4])}, …)'
        out.append(f'<div class="limit"><span class="chip limit-chip">limit</span> {what} {e(codes)}</div>')
    return ''.join(out)


class Catalog:
    def __init__(self, ser):
        self.by = {n: g for n, g in ser.groupby('Student Eligibility Rule')}

    def leaf(self, rows):
        r = rows.iloc[0]
        t = r['Rule Type']
        items, dummies = courses(r['All Courses Including Courses from Smart Lists'])
        n = int(r['Number of Courses'] or 0)
        qual = '' if t == 'Grade Requirement' or r['Qualifier'] in ('has completed', None) or pd.isna(r['Qualifier']) else f' <span class="chip">{e(r["Qualifier"])}</span>'
        dummy = f'<div class="muted small">plus {dummies} Workday placeholder course{"s" if dummies > 1 else ""} (DUMMY …)</div>' if dummies else ''
        if t == 'Course Requirement':
            if len(items) == 1 and r['Selector'] != 'any' or len(items) == 1 and n <= 1:
                head, body = f'<span class="code">{e(items[0].split(" - ")[0])}</span> {e(items[0].partition(" - ")[2])}', ''
            else:
                head = 'All of' if r['Selector'] == 'all' else f'Any {n} of' if n > 1 else 'One of'
                body = course_list(items, r['Smart Lists'])
        elif t == 'Hour Requirement':
            head, body = f'{int(r["Hours"])} hours from', course_list(items, r['Smart Lists'])
        elif t == 'Grade Requirement':
            head, body = e(' '.join(str(r['Eligibility Rule Meaning']).split())), ''
        else:
            head, body = f'<span class="chip">{e(t)}</span> {e(r["Eligibility Rule Meaning"])}', ''
        return (f'<div class="leaf"><div class="leaf-head">{head} {grade_chip(r)}{qual}</div>'
                f'{body}{dummy}{limit_html(rows)}</div>')

    def tree(self, name, seen=()):
        """Expression tree: ('leaf', html) | (op, [children]) with op 'all', 'any' or 'mixed'."""
        if name in seen:
            return ('leaf', f'<div class="leaf warn">Cycle: {e(name)}</div>')
        g = self.by[name]
        if g['Rule Type'].iloc[0] != 'Combination':
            return ('leaf', self.leaf(g))
        frames = [{'items': [], 'ops': set(), 'before': None}]
        for i, (_, line) in enumerate(g.sort_values('Order').iterrows()):
            subs = [self.tree(s.strip(), seen + (name,)) for s in str(line['Student Eligibility Rules']).split('\n') if s.strip()]
            sel = line['Selector for Combination Eligibility Rule']
            n = int(line['Number of Rules'] or 0)  # for 'any': how many sub-rules must be met
            sel = f'any{n}' if sel == 'any' and n > 1 else sel
            operand = subs[0] if len(subs) == 1 else (sel, subs)
            pending = None if i == 0 else line['And/Or']
            for _ in str(line['Open Parenthesis']) if pd.notna(line['Open Parenthesis']) else '':
                frames.append({'items': [], 'ops': set(), 'before': pending})
                pending = None
            top = frames[-1]
            if pending:
                top['ops'].add(pending)
            top['items'].append((pending, operand))
            for _ in str(line['Close Parenthesis']) if pd.notna(line['Close Parenthesis']) else '':
                done = frames.pop()
                if done['before']:
                    frames[-1]['ops'].add(done['before'])
                frames[-1]['items'].append((done['before'], self.close(done)))
        while len(frames) > 1:  # unbalanced: close what is left
            done = frames.pop(); frames[-1]['items'].append((done['before'], self.close(done)))
        return self.close(frames[0])

    @staticmethod
    def close(frame):
        if len(frame['items']) == 1:
            return frame['items'][0][1]
        if len(frame['ops']) > 1:
            return ('mixed', frame['items'])
        op = 'all' if frame['ops'] == {'And'} else 'any'
        kids = []
        for _, k in frame['items']:  # merge same-op children
            kids.extend(k[1] if k[0] == op else [k])
        return (op, kids)

    def render(self, node):
        kind, val = node
        if kind == 'leaf':
            return val
        if kind == 'mixed':
            parts = ''.join(f'<div class="op-sep">{e(op.upper())}</div>' * bool(op) + self.render(k) for op, k in val)
            return f'<div class="group mixed"><div class="group-label">In order (Workday’s precedence unclear)</div>{parts}</div>'
        label = 'All of these' if kind == 'all' else 'Any one of these' if kind == 'any' else f'Any {kind[3:]} of these'
        return f'<div class="group {kind[:3]}"><div class="group-label">{label}</div>{"".join(self.render(k) for k in val)}</div>'


def program_html(cat, pos, prog):
    rows = pos[pos['Program of Study'] == prog]
    reqs = rows.dropna(subset=['Student Eligibility Rule'])
    first = rows.iloc[0]
    items = []
    for _, q in reqs.iterrows():
        rule = q['Student Eligibility Rule']
        g = cat.by[rule].iloc[0]
        custom = ''
        if g['Use Custom Meaning'] == 'Yes' and pd.notna(g['Custom Eligibility Rule Meaning']):
            custom = f'<blockquote>{e(" ".join(str(g["Custom Eligibility Rule Meaning"]).split()))}</blockquote>'
        items.append(f'<li class="req"><div class="req-name">{e(q["Academic Requirement"])}</div>'
                     f'<div class="req-body">{cat.render(cat.tree(rule))}{custom}</div></li>')
    return (f'<section class="program"><h3>{e(prog)}</h3>'
            f'<p class="meta"><span class="code">{e(first["Code"])}</span> · {e(first["Owning Academic Unit"])} · '
            f'{len(reqs)} requirements</p><ol class="reqs">{"".join(items)}</ol></section>')


STYLE = """
:root {
  /* Reference-sheet layout: one column of requirement rows, Workday's label in a narrow left rail. */
  --bg: #f6f7f9; --surface: #ffffff; --ink: #1b2330; --muted: #5b6575; --line: #dde2ea;
  --accent: #1f5f8b; --accent-soft: #e6f0f7; --warn: #8a5a00; --warn-soft: #fbf1dc;
  --font-body: "IBM Plex Sans", system-ui, -apple-system, "Segoe UI", sans-serif;
  --font-mono: "IBM Plex Mono", ui-monospace, "SFMono-Regular", Menlo, monospace;
  color-scheme: light;
}
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) {
  --bg: #12161d; --surface: #1a2029; --ink: #e3e8ef; --muted: #98a3b3; --line: #2c3542;
  --accent: #7fb6dd; --accent-soft: #1d2e3c; --warn: #e7b85c; --warn-soft: #33290f; color-scheme: dark; } }
:root[data-theme="dark"] {
  --bg: #12161d; --surface: #1a2029; --ink: #e3e8ef; --muted: #98a3b3; --line: #2c3542;
  --accent: #7fb6dd; --accent-soft: #1d2e3c; --warn: #e7b85c; --warn-soft: #33290f; color-scheme: dark; }
* { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--ink); font: 15px/1.5 var(--font-body); }
main { max-width: 1040px; margin: 0 auto; padding: 32px 20px 64px; display: grid; gap: 28px; }
h1 { font-size: 28px; line-height: 1.2; margin: 0; text-wrap: balance; }
h2 { font-size: 21px; margin: 0; text-wrap: balance; }
h3 { font-size: 17px; margin: 0; }
p { margin: 0; max-width: 68ch; }
a { color: var(--accent); }
a:focus-visible, summary:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
.intro { display: grid; gap: 10px; }
.muted { color: var(--muted); } .small { font-size: 13px; }
nav { display: flex; flex-wrap: wrap; gap: 8px; }
nav a { padding: 6px 12px; border: 1px solid var(--line); border-radius: 999px; background: var(--surface); text-decoration: none; }
.group-block { display: grid; gap: 16px; scroll-margin-top: 16px; }
.note { background: var(--warn-soft); color: var(--ink); border-left: 3px solid var(--warn); padding: 10px 14px; border-radius: 4px; max-width: 80ch; }
.program { background: var(--surface); border: 1px solid var(--line); border-radius: 8px; padding: 18px 20px; display: grid; gap: 6px; }
.meta { color: var(--muted); font-size: 13px; }
.reqs { list-style: none; margin: 8px 0 0; padding: 0; display: grid; }
.req { display: grid; grid-template-columns: minmax(150px, 240px) 1fr; gap: 16px; padding: 12px 0; border-top: 1px solid var(--line); }
.req-name { color: var(--muted); font-size: 13px; }
.req-body { display: grid; gap: 8px; min-width: 0; }
.leaf { display: grid; gap: 4px; }
.leaf-head { font-weight: 500; }
.code { font-family: var(--font-mono); font-size: 13px; font-weight: 500; white-space: nowrap; }
.title { color: var(--ink); }
.courses { list-style: none; margin: 0; padding: 0; display: grid; gap: 2px; }
.courses li { display: flex; gap: 8px; align-items: baseline; }
details.courses-more summary { cursor: pointer; color: var(--accent); }
details.courses-more .courses { margin-top: 6px; max-height: 320px; overflow-y: auto; }
.chip { display: inline-block; font-size: 12px; font-weight: 500; padding: 1px 8px; border-radius: 999px; background: var(--accent-soft); color: var(--accent); white-space: nowrap; }
.limit { font-size: 13px; color: var(--muted); }
.limit-chip { background: var(--warn-soft); color: var(--warn); }
.group { border-left: 2px solid var(--accent); padding: 2px 0 2px 12px; display: grid; gap: 8px; }
.group.any { border-left-style: dashed; }
.group.mixed { border-left-color: var(--warn); }
.group-label { font-size: 12px; font-weight: 600; letter-spacing: .04em; text-transform: uppercase; color: var(--accent); }
.mixed > .group-label { color: var(--warn); }
.op-sep { font-size: 12px; font-weight: 600; color: var(--warn); }
blockquote { margin: 0; padding: 6px 10px; border-left: 3px solid var(--line); color: var(--muted); font-size: 13px; }
.legend { display: flex; flex-wrap: wrap; gap: 8px 20px; font-size: 13px; color: var(--muted); }
.legend span { display: inline-flex; gap: 6px; align-items: center; }
.swatch { width: 14px; height: 14px; border-left: 2px solid var(--accent); }
.swatch.any { border-left-style: dashed; }
@media (max-width: 640px) { .req { grid-template-columns: 1fr; gap: 6px; } }
@media (prefers-reduced-motion: reduce) { * { scroll-behavior: auto; } }
"""


def page(dfs, groups):
    pos, ar, ser, meta = pickle.load(open(dfs, 'rb'))
    cat = Catalog(ser)
    nav, blocks = [], []
    for anchor, progs in groups:
        label = ' + '.join(progs)
        nav.append(f'<a href="#{e(anchor)}">{e(label)}</a>')
        note = f'<p class="note">{e(NOTES[anchor])}</p>' if anchor in NOTES else ''
        blocks.append(f'<section class="group-block" id="{e(anchor)}"><h2>{e(label)}</h2>{note}'
                      f'{"".join(program_html(cat, pos, p) for p in progs)}</section>')
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Programs Rebuilt from Workday</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@400;500;600&display=swap" rel="stylesheet">
<style>{STYLE}</style></head><body><main>
<header class="intro">
<h1>Programs Rebuilt from Workday</h1>
<p>Each program below is generated only from the structured fields of IT’s provisional November 2026 export of Workday’s program-of-study requirements: who counts, how many, how many hours, which grade, and which limits. It is an experiment, not a catalog and not an official record.</p>
<p class="muted">Left column: Workday’s name for each requirement. Right: what its rule actually checks. Requirements appear in Workday’s order, which is alphabetical by name. Course credits, section headings, and the catalog’s policy text are not in the data, so they are missing here.</p>
<div class="legend"><span><i class="swatch"></i>All of these</span><span><i class="swatch any"></i>Any one (or N) of these</span><span><span class="chip grade">grade ≥ C</span>minimum grade</span><span><span class="chip limit-chip">limit</span>cap on hours or repeats</span></div>
</header>
<nav aria-label="Programs">{''.join(nav)}</nav>
{''.join(blocks)}
</main></body></html>"""


if __name__ == '__main__':
    dfs, out, *specs = sys.argv[1:]
    groups = [(s.split('=', 1)[0], s.split('=', 1)[1].split('+')) for s in specs]
    open(out, 'w', encoding='utf-8').write(page(dfs, groups))
    print('wrote', out)
