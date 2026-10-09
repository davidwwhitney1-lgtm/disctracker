#!/usr/bin/env python3
"""Turn the XIAO's underside VBAT/GND pads (19, 20) into plated holes so they can be
soldered from the sensor face after the XIAO is soldered flat. usage: xiao_fp.py <pretty dir>"""
import sys, pcbnew
from pcbnew import FromMM, VECTOR2I
lib = sys.argv[1]
fp = pcbnew.FootprintLoad(lib, "XIAO-nRF52840-SMD")
for p in fp.Pads():
    if p.GetNumber() in ("19", "20"):
        p.SetAttribute(pcbnew.PAD_ATTRIB_PTH)
        p.SetLayerSet(pcbnew.PAD.PTHMask())
        d = 0.6
        p.SetDrillSize(VECTOR2I(FromMM(d), FromMM(d)))
for g in fp.GraphicalItems():   # outline overhangs the USB-C flat: keep it on fab only
    if g.GetLayer() == pcbnew.F_SilkS and g.GetClass() == "PCB_SHAPE":
        g.SetLayer(pcbnew.F_Fab)
fp.SetLibDescription("Seeed XIAO nRF52840, SMD. Pads 19-20 made plated through-holes (DiscTracker). "
                     "Source: Seeed OPL KiCad library, CC BY-SA 4.0")
pcbnew.FootprintSave(lib, fp)
print("ok")
