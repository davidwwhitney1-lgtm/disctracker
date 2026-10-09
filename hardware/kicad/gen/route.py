#!/usr/bin/env python3
"""Autoroute with Freerouting, import the result, add outer GND pours and fill all zones.
usage: route.py <board.kicad_pcb> <freerouting.jar> <workdir> [passes]"""
import subprocess, sys, pcbnew
from pcbnew import FromMM
pcb, jar, work = sys.argv[1:4]
passes = sys.argv[4] if len(sys.argv) > 4 else "100"
b = pcbnew.LoadBoard(pcb)
assert pcbnew.ExportSpecctraDSN(b, f"{work}/board.dsn")
# keep signals off the inner planes: mark In1 (GND) as a power layer; In2 carries some signals plus the +3V3 pour
import re
dsn = open(f"{work}/board.dsn").read()
dsn = re.sub(r"(\(layer In1\.Cu\s*\(type )signal", r"\1power", dsn)
open(f"{work}/board.dsn", "w").write(dsn)
subprocess.run(["java", "-jar", jar, "-de", f"{work}/board.dsn", "-do", f"{work}/board.ses",
                "-mp", passes, "--gui.enabled=false"], check=True)
assert pcbnew.ImportSpecctraSES(b, f"{work}/board.ses")
gnd = b.FindNet("/GND")
for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
    z = pcbnew.ZONE(b)
    z.SetLayer(layer); z.SetNet(gnd)
    o = z.Outline(); o.NewOutline()
    for x, y in ((70, 70), (130, 70), (130, 130), (70, 130)):
        o.Append(FromMM(x), FromMM(y))
    z.SetLocalClearance(FromMM(0.2)); z.SetMinThickness(FromMM(0.2))
    z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
    z.SetThermalReliefGap(FromMM(0.2)); z.SetThermalReliefSpokeWidth(FromMM(0.25))
    b.Add(z)
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
pcbnew.SaveBoard(pcb, b)
print("tracks", sum(1 for t in b.GetTracks() if t.GetClass() == "PCB_TRACK"),
      "vias", sum(1 for t in b.GetTracks() if t.GetClass() == "PCB_VIA"))
