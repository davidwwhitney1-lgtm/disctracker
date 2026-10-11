#!/usr/bin/env python3
"""Export the sensor board's outline, holes and part envelopes to board_parts.json for housing.py.

usage: python3 board_parts.py ../kicad/disctracker_sensor.kicad_pcb board_parts.json
Runs with KiCad's Python (pcbnew). Positions are in the housing/PCB math frame: origin = board centre (U1),
+X toward the USB-C flat, +Y up as seen from the sensor face. Each part is a box = its pad/body extent on
its side plus a height (mm) from the table below; "side" is "sensor" (F.Cu, faces the lid) or "xiao"
(B.Cu, faces the cover). The XIAO module itself is modelled in housing.py from Seeed's STEP data.
"""
import json, sys
import pcbnew
from pcbnew import ToMM

HEIGHT = {                    # max body height above the board, mm
    "LGA-14": 0.86,           # LSM6DSV320X, 0.83 typ
    "WLP-4": 0.45,            # MMC5603NJ
    "R_0402": 0.40, "C_0402": 0.55, "C_0603": 0.90,
    "SolderJumper": 0.05, "TestPoint_Pad": 0.05,
    "Buzzer_CUI_CPT-9019S": 1.90,
    "SolderWirePad": 1.60,    # battery wire + solder fillet
}

b = pcbnew.LoadBoard(sys.argv[1])
parts = []
for fp in b.GetFootprints():
    ref, name = fp.GetReference(), fp.GetFPID().GetLibItemName().wx_str()
    if ref.startswith(("H", "M")):
        continue
    h = next((v for k, v in HEIGHT.items() if k in name), None)
    if h is None:
        raise SystemExit(f"no height for {ref} {name}")
    side = "xiao" if fp.IsFlipped() else "sensor"
    # body extent: courtyard shrunk by the usual 0.25 mm margin, never smaller than the pads
    cy = fp.GetCourtyard(pcbnew.B_CrtYd if fp.IsFlipped() else pcbnew.F_CrtYd)
    if cy.OutlineCount():
        bb = cy.BBox(); m = 0.25
        x0, x1, y0, y1 = ToMM(bb.GetLeft()) + m, ToMM(bb.GetRight()) - m, ToMM(bb.GetTop()) + m, ToMM(bb.GetBottom()) - m
    else:
        bb = fp.GetBoundingBox(False, False)
        x0, x1, y0, y1 = ToMM(bb.GetLeft()), ToMM(bb.GetRight()), ToMM(bb.GetTop()), ToMM(bb.GetBottom())
    for p in fp.Pads():
        pb = p.GetBoundingBox()
        x0, x1 = min(x0, ToMM(pb.GetLeft())), max(x1, ToMM(pb.GetRight()))
        y0, y1 = min(y0, ToMM(pb.GetTop())), max(y1, ToMM(pb.GetBottom()))
    dnp = bool(fp.GetAttributes() & pcbnew.FP_DNP) if hasattr(pcbnew, "FP_DNP") else False
    parts.append({"ref": ref, "fp": name, "side": side, "dnp": dnp, "h": h,
                  "x": [round(x0 - 100, 3), round(x1 - 100, 3)], "y": [round(100 - y1, 3), round(100 - y0, 3)]})
holes = []
for fp in b.GetFootprints():
    if fp.GetReference().startswith("H"):
        p = fp.GetPosition()
        holes.append({"ref": fp.GetReference(), "x": round(ToMM(p.x) - 100, 4), "y": round(100 - ToMM(p.y), 4),
                      "d": round(ToMM(list(fp.Pads())[0].GetDrillSize().x), 3)})
json.dump({"source": "hardware/kicad/disctracker_sensor.kicad_pcb", "board_r": 28.0, "flat_x": 26.5,
           "thickness": round(ToMM(b.GetDesignSettings().GetBoardThickness()), 3),
           "holes": sorted(holes, key=lambda h: h["ref"]), "parts": sorted(parts, key=lambda p: p["ref"])},
          open(sys.argv[2], "w"), indent=1)
print(f"{len(parts)} parts, {len(holes)} holes")
