#!/usr/bin/env python3
"""Add GND stitching vias wherever there is free space, tying the outer GND pours to the
In1 GND plane, then refill zones. usage: stitch.py <board.kicad_pcb> [pitch_mm]"""
import math, sys, pcbnew
from pcbnew import FromMM, ToMM, VECTOR2I

pcb = sys.argv[1]
pitch = float(sys.argv[2]) if len(sys.argv) > 2 else 2.0
b = pcbnew.LoadBoard(pcb)
gnd = b.FindNet("/GND")
VIA_D, VIA_DRILL, CLR = 0.45, 0.25, 0.25
CX, CY, R_OK, FLAT = 100.0, 100.0, 26.6, 125.6   # board center, usable radius, usable x before the flat

def seg_dist(px, py, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    L = dx * dx + dy * dy
    t = 0 if L == 0 else max(0, min(1, ((px - ax) * dx + (py - ay) * dy) / L))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))

obst = []   # (kind, data)
for t in b.GetTracks():
    if t.GetClass() == "PCB_TRACK" and t.GetNetCode() != gnd.GetNetCode():
        obst.append(("seg", (ToMM(t.GetStart().x), ToMM(t.GetStart().y), ToMM(t.GetEnd().x), ToMM(t.GetEnd().y), ToMM(t.GetWidth()) / 2)))
    elif t.GetClass() == "PCB_VIA":
        obst.append(("pt", (ToMM(t.GetPosition().x), ToMM(t.GetPosition().y), ToMM(t.GetWidth(pcbnew.F_Cu)) / 2)))
for fp in b.GetFootprints():
    for p in fp.Pads():     # no via near any pad, including GND pads (no via-in-pad)
        bb = p.GetBoundingBox()
        obst.append(("box", (ToMM(bb.GetLeft()), ToMM(bb.GetTop()), ToMM(bb.GetRight()), ToMM(bb.GetBottom()))))
    if fp.GetReference().startswith("H"):
        obst.append(("pt", (ToMM(fp.GetPosition().x), ToMM(fp.GetPosition().y), 1.6)))
    cy = fp.GetCourtyard(pcbnew.F_CrtYd if not fp.IsFlipped() else pcbnew.B_CrtYd)
    if fp.GetReference()[0] in "U" and cy.OutlineCount():   # keep vias out from under the sensors
        bb = cy.BBox()
        obst.append(("box", (ToMM(bb.GetLeft()), ToMM(bb.GetTop()), ToMM(bb.GetRight()), ToMM(bb.GetBottom()))))

def free(x, y):
    r = VIA_D / 2
    if math.hypot(x - CX, y - CY) > R_OK - r or x > FLAT - r:
        return False
    for k, d in obst:
        if k == "seg" and seg_dist(x, y, *d[:4]) < r + d[4] + CLR:
            return False
        if k == "pt" and math.hypot(x - d[0], y - d[1]) < r + d[2] + CLR:
            return False
        if k == "box":
            dx = max(d[0] - x, 0, x - d[2]); dy = max(d[1] - y, 0, y - d[3])
            if math.hypot(dx, dy) < r + CLR:
                return False
    return True

added = 0
n = int(30 / pitch)
for i in range(-n, n + 1):
    for j in range(-n, n + 1):
        x, y = CX + i * pitch, CY + j * pitch
        if free(x, y):
            v = pcbnew.PCB_VIA(b)
            v.SetPosition(VECTOR2I(FromMM(x), FromMM(y)))
            v.SetWidth(FromMM(VIA_D)); v.SetDrill(FromMM(VIA_DRILL)); v.SetNet(gnd)
            b.Add(v); added += 1
            obst.append(("pt", (x, y, VIA_D / 2)))
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
pcbnew.SaveBoard(pcb, b)
print("stitching vias added:", added)
