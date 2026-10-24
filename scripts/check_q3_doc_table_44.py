"""Verify docs/q3_scaling.md 4.4's size-axis table against data/q3_sweep.txt (same rule as
check_doc_table.py: the verdict gap comes from the data file's own column, never from the
difference of rounded printed values)."""
import re
import sys

with open(r"C:\Work\~\TFIM_QEC_Frustration\docs\q3_scaling.md", encoding="utf-8") as fh:
    doc = fh.read()
with open(r"C:\Work\~\TFIM_QEC_Frustration\data\q3_sweep.txt", encoding="utf-8") as fh:
    data = fh.read()

rows = {}
for line in data.splitlines():
    m = re.match(r"\s+(\d+)\s+([\d.]+)\s+(\d+)\s+(early|late)\s+(bare raw|bare \+ Gauss|Iceberg|Iceberg \+ Gauss)"
                 r"\s+([\d.]+)\s+(\S+)\s+([\d.]+)\s+(True|False)\s+([\d.]+)\s+([\d.]+)\s+(\d+)", line)
    if m:
        rows[(int(m[1]), float(m[2]), int(m[3]), m[4], m[5])] = (float(m[6]), float(m[8]), float(m[10]))

# | N = 18, h = 0.3, lam = 1 | 22 | 36 | r ± se ×c | r ± se ×c | r ± se ×c | verdict |
pat = re.compile(r"^\| N = (\d+), h = ([\d.]+), \u03bb = (\d) \| (\d+) \| (\d+) \| "
                 r"([\d.]+) \u00b1 ([\d.]+) \u00d7([\d.]+) \| ([\d.]+) \u00b1 ([\d.]+) \u00d7([\d.]+) \| "
                 r"([\d.]+) \u00b1 ([\d.]+) \u00d7([\d.]+) \| (.+) \|$")
bad = checked = 0
for line in doc.splitlines():
    m = pat.match(line.strip())
    if not m:
        continue
    N, h, lam = int(m[1]), float(m[2]), int(m[3])
    trip = {"bare + Gauss": (float(m[6]), float(m[7]), float(m[8])),
            "Iceberg": (float(m[9]), float(m[10]), float(m[11])),
            "Iceberg + Gauss": (float(m[12]), float(m[13]), float(m[14]))}
    for mode, (r, se, cost) in trip.items():
        key = (N, h, lam, "early", mode)
        if key not in rows:
            print(f"MISSING in data: {key}"); bad += 1; continue
        dr, dse, dcost = rows[key]
        for name, a, b, tol in (("residual", r, dr, 5e-5), ("se", se, dse, 5e-5), ("cost", cost, dcost, 6e-3)):
            if abs(a - b) > tol:
                print(f"MISMATCH {key} {name}: doc {a} vs data {b}"); bad += 1
        checked += 1
    # verdict text must match the data file's verdict column for this cell
    want = re.search(rf"^\s+{N}\s+{h:g}\s+{lam}\s+.*?(better by [\d.]+|unresolved \(within combined SE\))\s*$",
                     data, re.MULTILINE)
    doc_verdict = m[15].replace("**", "").replace("bare + Gauss better by", "better by").strip()
    if not want:
        print(f"MISSING verdict row for N={N} h={h} lam={lam}"); bad += 1
    elif want[1] != doc_verdict:
        print(f"MISMATCH verdict N={N} h={h} lam={lam}: doc '{doc_verdict}' vs data '{want[1]}'"); bad += 1
    # the window column must match the cell's 'ice steps' in section 1
    w = re.search(rf"^\s+{N}\s+\S+\s+\S+\s+{h:g}\s+{lam}\s+(\d+)\s+(\d+)\s", data, re.MULTILINE)
    if w and int(w[2]) != int(m[5]):
        print(f"MISMATCH window N={N} h={h} lam={lam}: doc {m[5]} vs data {w[2]}"); bad += 1
    if w and int(w[1]) != int(m[4]):
        print(f"MISMATCH phys N={N} h={h} lam={lam}: doc {m[4]} vs data {w[1]}"); bad += 1
if checked == 0:
    print("4.4: NO rows found in docs/q3_scaling.md 4.4 - it is still PENDING (unpublished), so "
          "there is nothing to check. This is NOT a pass: re-run once 4.4 is written.")
    sys.exit(2)
print(f"4.4: checked {checked} doc/data triples + verdict/window/phys per cell; mismatches: {bad}")
sys.exit(1 if bad else 0)
