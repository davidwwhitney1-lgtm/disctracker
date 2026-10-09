#!/usr/bin/env python3
"""Hand fixes after autorouting (specific to the current route):
- replace the +3V3 track the router wrapped around U6 ball A1 with a direct B1 -> C11 link
- delete two dead INT1 stubs
usage: fixups.py <board.kicad_pcb>"""
import sys, pcbnew
from pcbnew import ToMM, FromMM, VECTOR2I
b = pcbnew.LoadBoard(sys.argv[1])
P = lambda v: (round(ToMM(v.x), 2), round(ToMM(v.y), 2))
kill = {((102.1, 121.68), (99.43, 124.35)), ((99.43, 124.35), (99.43, 125.01)),
        ((99.43, 125.01), (99.62, 125.2)), ((99.62, 125.2), (99.8, 125.2))}
# INT1 looped tight around C2 and sealed its +3V3 pad in: take it wider
INT1_OLD = {((97.75, 102.83), (97.75, 101.84)), ((98.34, 103.42), (97.75, 102.83)), ((101.67, 103.42), (98.34, 103.42))}
doomed = []
for t in b.GetTracks():
    if t.GetClass() != "PCB_TRACK":
        continue
    ends = (P(t.GetStart()), P(t.GetEnd()))
    if t.GetNetname() == "/+3V3" and (ends in kill or ends[::-1] in kill):
        doomed.append(t)
    elif t.GetNetname() == "/IMU_INT1" and abs(ToMM(t.GetLength()) - 0.5162) < 0.001:
        doomed.append(t)
    elif t.GetNetname() == "/IMU_INT1" and (ends in INT1_OLD or ends[::-1] in INT1_OLD):
        doomed.append(t)
for t in doomed:
    b.Remove(t)
def add(a, c, netname, w=0.15):
    have = {(P(t.GetStart()), P(t.GetEnd())) for t in b.GetTracks() if t.GetClass() == "PCB_TRACK"}
    if (a, c) in have or (c, a) in have:
        return
    t = pcbnew.PCB_TRACK(b)
    t.SetStart(VECTOR2I(FromMM(a[0]), FromMM(a[1]))); t.SetEnd(VECTOR2I(FromMM(c[0]), FromMM(c[1])))
    t.SetWidth(FromMM(w)); t.SetLayer(pcbnew.F_Cu); t.SetNet(b.FindNet(netname)); b.Add(t)
for a, c in (((97.75, 101.84), (97.75, 103.6)), ((97.75, 103.6), (98.35, 104.2)),
             ((98.35, 104.2), (101.67, 104.2)), ((101.67, 104.2), (101.67, 103.42))):
    add(a, c, "/IMU_INT1", 0.127)
v = pcbnew.PCB_VIA(b); v.SetPosition(VECTOR2I(FromMM(98.22), FromMM(103.4)))
v.SetWidth(FromMM(0.45)); v.SetDrill(FromMM(0.25)); v.SetNet(b.FindNet("/+3V3")); b.Add(v)
add((98.22, 103.4), (98.22, 102.5), "/+3V3")
for a, c in (((99.8, 125.2), (99.52, 125.48)), ((99.52, 125.48), (98.0, 125.48)),       # U6 B1 -> C11
             ((99.5, 101.22), (98.22, 102.5)),                                              # U1 VDDIO -> C2
             ((119.5, 100.9125), (119.5, 101.35)), ((119.5, 101.35), (118.6, 101.35)),
             ((118.6, 101.35), (118.22, 102.5))):                                           # U2 VDDIO -> C4
    add(a, c, "/+3V3")
pcbnew.SaveBoard(sys.argv[1], b)
print("removed", len(doomed), "segments")
