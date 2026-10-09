#!/usr/bin/env python3
"""Make JLCPCB assembly files (sensor face only) from KiCad's pos export.
usage: jlc.py fab/pos_front.csv fab/
LCSC numbers for passives are JLCPCB "basic" parts - confirm stock when ordering.
LSM6DSV320X has no LCSC number here: order it in, or consign it."""
import csv, sys, collections

pos_csv, out = sys.argv[1], sys.argv[2]
LCSC = {  # (value, package) -> LCSC part
    ("100n", "C_0402_1005Metric"): "C1525",
    ("2.2u", "C_0402_1005Metric"): "C12530",
    ("4.7k", "R_0402_1005Metric"): "C25900",
    ("100k", "R_0402_1005Metric"): "C25741",
    ("33", "R_0402_1005Metric"): "C25105",
    ("100", "R_0402_1005Metric"): "C25076",
    ("MMC5603NJ", "WLP-4_0.86x0.86mm_P0.4mm"): "C404328",
    ("LSM6DSV320X", "LGA-14_3x2.5mm_P0.5mm_LayoutBorder3x4y"): "",
}
rows = list(csv.DictReader(open(pos_csv)))
bom = collections.OrderedDict()
with open(f"{out}/cpl_jlc.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["Designator", "Mid X", "Mid Y", "Layer", "Rotation"])
    for r in rows:
        if r["Package"].startswith("SolderJumper"):
            continue  # JP1 is bridged by hand
        w.writerow([r["Ref"], r["PosX"] + "mm", r["PosY"] + "mm", "Top", r["Rot"]])
        key = (r["Val"], r["Package"])
        bom.setdefault(key, []).append(r["Ref"])
with open(f"{out}/bom_jlc.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["Comment", "Designator", "Footprint", "LCSC Part #"])
    for (val, pkg), refs in bom.items():
        w.writerow([val, ",".join(refs), pkg, LCSC.get((val, pkg), "")])
print("cpl", sum(len(v) for v in bom.values()), "parts;", len(bom), "bom lines")
