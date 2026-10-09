#!/usr/bin/env python3
"""Give specific GND / +3V3 pads their own via to the matching inner plane (short track + via at the nearest
free spot), make outer GND pours drop unconnected islands, refill.
usage: padvia.py <board.kicad_pcb> REF:PAD [REF:PAD ...]"""
import math, sys, pcbnew
from pcbnew import FromMM, ToMM, VECTOR2I

pcb = sys.argv[1]
b = pcbnew.LoadBoard(pcb)
gnd = b.FindNet("/GND")
VIA_D, CLR = 0.45, 0.15

def items():
    for t in b.GetTracks():
        yield t
    for fp in b.GetFootprints():
        for p in fp.Pads():
            yield p

SENSORS = []
for fp in b.GetFootprints():   # no vias under the motion sensors / magnetometer (ST + MEMSIC layout advice)
    if fp.GetReference().startswith("U"):
        bb = fp.GetCourtyard(pcbnew.F_CrtYd).BBox()
        SENSORS.append((ToMM(bb.GetLeft()), ToMM(bb.GetTop()), ToMM(bb.GetRight()), ToMM(bb.GetBottom())))

def ok(x, y, own, gnd):
    """via at (x, y) and the track from the pad must clear every other-net copper item"""
    if any(l - 0.25 < x < r + 0.25 and t - 0.25 < y < bt + 0.25 for l, t, r, bt in SENSORS):
        return None
    v = pcbnew.PCB_VIA(b); v.SetPosition(VECTOR2I(FromMM(x), FromMM(y)))
    v.SetWidth(FromMM(VIA_D)); v.SetDrill(FromMM(0.25)); v.SetNet(gnd)
    t = pcbnew.PCB_TRACK(b); t.SetStart(own.GetPosition()); t.SetEnd(v.GetPosition())
    t.SetWidth(FromMM(0.15)); t.SetLayer(own.GetLayer() if own.GetLayer() >= 0 else pcbnew.F_Cu); t.SetNet(gnd)
    for it in items():
        if it is own:
            continue
        same = it.GetNetCode() == gnd.GetNetCode()
        for layer in (pcbnew.F_Cu, pcbnew.B_Cu, pcbnew.In2_Cu):
            if not it.IsOnLayer(layer):
                continue
            sv = v.GetEffectiveShape(layer)
            si = it.GetEffectiveShape(layer)
            gap = FromMM(CLR if not same else 0.1)
            if it.GetClass() == "PAD" and same and it.GetParent() == own.GetParent():
                gap = FromMM(0.15)
            if sv.Collide(si, gap):
                return None
            if layer == t.GetLayer() and not same and t.GetEffectiveShape(layer).Collide(si, FromMM(CLR)):
                return None
    return v, t

for spec in sys.argv[2:]:
    ref, pad = spec.split(":")
    fp = b.FindFootprintByReference(ref)
    p = [q for q in fp.Pads() if q.GetNumber() == pad][0]
    px, py = ToMM(p.GetPosition().x), ToMM(p.GetPosition().y)
    done = False
    for r in [0.6 + 0.1 * k for k in range(30)]:
        for a in range(0, 360, 15):
            x, y = px + r * math.cos(math.radians(a)), py + r * math.sin(math.radians(a))
            res = ok(x, y, p, p.GetNet())
            if res:
                b.Add(res[0]); b.Add(res[1]); done = True
                print(f"{spec}: via at ({x:.2f}, {y:.2f}), {r:.1f} mm away")
                break
        if done:
            break
    if not done:
        print(f"{spec}: no free spot found")

for z in b.Zones():
    if not z.GetIsRuleArea() and z.GetLayer() in (pcbnew.F_Cu, pcbnew.B_Cu):
        z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
pcbnew.SaveBoard(pcb, b)
