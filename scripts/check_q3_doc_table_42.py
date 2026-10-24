"""Verify every number in docs/q3_scaling.md 4.2 / 4.1 against data/q3_sweep.txt."""
import re
import sys

with open(r"C:\Work\~\TFIM_QEC_Frustration\docs\q3_scaling.md", encoding="utf-8") as fh:
    doc = fh.read()
with open(r"C:\Work\~\TFIM_QEC_Frustration\data\q3_sweep.txt", encoding="utf-8") as fh:
    data = fh.read()

# data: head-to-head section rows -> (N,h,lam) -> {mode: (residual, se, cost)}
rows = {}
for line in data.splitlines():
    m = re.match(r"\s+(\d+)\s+([\d.]+)\s+(\d+)\s+(early|late)\s+(bare raw|bare \+ Gauss|Iceberg|Iceberg \+ Gauss)"
                 r"\s+([\d.]+)\s+(\S+)\s+([\d.]+)\s+(True|False)\s+([\d.]+)\s+([\d.]+)\s+(\d+)", line)
    if m:
        key = (int(m[1]), float(m[2]), int(m[3]), m[4], m[5])
        rows[key] = (float(m[6]), float(m[8]), float(m[10]))

# doc 4.2 markdown rows: | h | lam | bare+Gauss | Iceberg | Ice+Gauss | verdict |
bad = 0
pat = re.compile(r"^\| (0\.\d) \| (\d) \| ([\d.]+) ± ([\d.]+) ×([\d.]+) \| ([\d.]+) ± ([\d.]+) ×([\d.]+) \| "
                 r"([\d.]+) ± ([\d.]+) ×([\d.]+) \| bare \+ Gauss by ([\d.]+) \|$")
checked = 0
for line in doc.splitlines():
    m = pat.match(line.strip())
    if not m:
        continue
    h, lam = float(m[1]), int(m[2])
    trip = {"bare + Gauss": (float(m[3]), float(m[4]), float(m[5])),
            "Iceberg": (float(m[6]), float(m[7]), float(m[8])),
            "Iceberg + Gauss": (float(m[9]), float(m[10]), float(m[11]))}
    for mode, (r, se, cost) in trip.items():
        key = (12, h, lam, "early", mode)
        if key not in rows:
            print(f"MISSING in data: {key}"); bad += 1; continue
        dr, dse, dcost = rows[key]
        for name, a, b, tol in (("residual", r, dr, 5e-5), ("se", se, dse, 5e-5),
                                ("cost", cost, dcost, 6e-3)):
            if abs(a - b) > tol:
                print(f"MISMATCH {key} {name}: doc {a} vs data {b}"); bad += 1
        checked += 1
    # The verdict gap is computed by the script from FULL-PRECISION residuals, so comparing it
    # to the difference of the printed (rounded) values is wrong by up to 1e-4. Compare against
    # the data file's own verdict column instead.
    want = re.search(rf"^\s+12\s+{h:g}\s+{lam}\s+.*better by ([\d.]+)\s*$", data, re.MULTILINE)
    if not want:
        print(f"MISSING verdict row for h={h} lam={lam}"); bad += 1
    elif abs(float(want[1]) - float(m[12])) > 1e-9:
        print(f"MISMATCH verdict at h={h} lam={lam}: doc {m[12]} vs data {want[1]}"); bad += 1
print(f"checked {checked} doc/data number triples ({len(rows)} data rows parsed); mismatches: {bad}")
sys.exit(1 if bad else 0)
