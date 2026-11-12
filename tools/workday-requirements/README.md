# Workday program-of-study requirements: exploration scripts

Exploratory Python scripts for IT's provisional export of Workday's program-of-study requirements (`2026-11_Program_of_Study_Requirements.xlsx`, November 2026). The workbook isn't committed: it's provisional and IT hasn't validated it. Pass its path on the command line.

Needs Python 3 with `pandas` and `openpyxl`.

## Workbook layout

| Sheet | Rows | What it holds |
|---|---|---|
| Program of Study Requirements | one per program × requirement | 330 programs; requirement name, Reference ID, rule type, rule name |
| Academic Requirements | one per requirement | requirement → eligibility rule (by Reference ID); 1,112 used by programs, 1,732 not |
| Student Eligibility Rules | one per rule, or one per combination line / limit line | the rule logic and the courses it accepts (smart lists expanded) |
| meta | | Workday's field definitions |

Joins: program → requirement on `Reference ID` = `Requirement Ref ID`; requirement → rule on `Eligibility Rule Ref ID` = rule `Reference ID`. Combination lines name their sub-rules by **name**, newline-separated (unique today, so this works).

How the rule fields read:
- **Combination rules** are infix expressions, one row per line, in `Order` (a, b, c, …). Each line applies its selector (`all` / `any`) to its sub-rules and joins the previous lines with `And`/`Or`. `Open Parenthesis` and `Close Parenthesis` group lines. For an `any` line, `Number of Rules` is how many sub-rules must be met ("any 2 of").
- **Course requirements:** `Selector` all/any, plus `Number of Courses` for "any N of".
- **Hour requirements:** `Hours`.
- **Grades:** `Grade` plus `Operator`; the grading scheme (Calvin Main vs Calvin Transfer, where AP/transfer credit is CR) appears only in `Eligibility Rule Meaning`.
- **Limits:** extra rows with `Class of Instance` set. "Up To Limit" caps hours from a course set; "Repeat Limit" caps registrations.
- **Indirect encodings:** some catalog wording is encoded as a complement. "At least 2 hours at the 300 level" becomes 12 hours with at most 10 from 100/200-level. "No more than 4 hours of BCHM" becomes 16 hours from BIOL plus 20 from BIOL and BCHM.
- **Placeholders:** `DUMMY 100`/`101`/`102` courses pad some repeat rules (CS 195 ×3).

## Scripts

Run `load.py` first; the others read its pickle. These are exploration scripts, not part of the app or its tests.

```sh
python3 load.py Program_of_Study_Requirements.xlsx dfs.pkl
```

| Script | What it does |
|---|---|
| `load.py xlsx out.pkl` | Reads the four sheets (header rows handled) into a pickle. |
| `resolve.py` | Library: `R(ser).courses(rule)` collects every course a rule tree accepts; `name_codes(text)` reads course codes (and ranges) from catalog-style text. |
| `joins.py pkl` | Key uniqueness and referential checks across sheets. |
| `structure.py pkl` | Multi-row rule layout, parentheses, sub-rule counts, core rules. |
| `misc.py pkl` | Field definitions, programs with no requirements, value counts of combination fields. |
| `cs.py pkl` | Program counts, and Computer Science, BCS's requirements. |
| `rules.py pkl "REQ: …" …` | Dumps one or more rules, following combination chains. |
| `compare.py pkl [out.pkl]` | For every requirement, compares the courses its name lists with the courses its rule accepts. |
| `wdcatalog.py pkl "Program" …` | Plain-text "catalog" of programs, built from rule fields only (not names). |
| `catalog_html.py pkl out.html "anchor=Program[+Program]" …` | The same as an HTML page with nested any/all groups. |

```sh
python3 catalog_html.py dfs.pkl out.html "bcs=Computer Science, BCS" \
    "nursing=Pre-nursing+Nursing, BSN" "biology=Biology, BS"
```
