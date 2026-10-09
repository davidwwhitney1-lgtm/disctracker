#!/usr/bin/env python3
"""Build the DiscTracker sensor-board PCB (placement, outline, planes, keepouts, silk).

usage: python3 pcb.py <project dir> <kicad netlist (kicadsexpr)>
Coordinates in this file are "math" millimetres seen from the sensor face:
origin = board center (U1), +X toward the USB-C flat, +Y up. KiCad's y axis points
down, so B(x, y) maps to (100 + x, 100 - y).
"""
import math, re, sys
import pcbnew
from pcbnew import FromMM, VECTOR2I

PRJ, NETLIST = sys.argv[1], sys.argv[2]
NAME = "disctracker_sensor"
OX, OY = 100.0, 100.0
R_BOARD = 28.0          # 56 mm round
FLAT_X = 26.5           # flat for the USB-C plug
STD = "/usr/share/kicad/footprints/"

def B(x, y):
    return VECTOR2I(FromMM(OX + x), FromMM(OY - y))

def M(v):  # board -> math
    return (pcbnew.ToMM(v.x) - OX, OY - pcbnew.ToMM(v.y))

# ------------------------------------------------------------------ netlist
net_src = open(NETLIST).read()
comps = {}
for m in re.finditer(r'\(comp \(ref "([^"]+)"\)\s*\(value "([^"]*)"\)\s*\(footprint "([^"]*)"\)(.*?)\(tstamps "([^"]+)"\)', net_src, re.S):
    ref, val, fp, body, ts = m.groups()
    comps[ref] = dict(value=val, fp=fp, uuid=ts)
pad_net = {}
for m in re.finditer(r'\(net \(code "\d+"\) \(name "([^"]+)"\)(.*?)\)\s*(?=\(net |\)\s*\)\s*$)', net_src, re.S):
    name = m.group(1)
    for r, p in re.findall(r'\(node \(ref "([^"]+)"\) \(pin "([^"]+)"\)', m.group(2)):
        pad_net[(r, p)] = name

board = pcbnew.NewBoard(f"{PRJ}/{NAME}.kicad_pcb")
board.SetCopperLayerCount(4)
ds = board.GetDesignSettings()
ds.SetBoardThickness(FromMM(0.8))
ds.m_MinClearance = FromMM(0.1)
ds.m_TrackMinWidth = FromMM(0.1)
ds.m_ViasMinSize = FromMM(0.45)
ds.m_ViasMinAnnularWidth = FromMM(0.1)
ds.m_HoleClearance = FromMM(0.2)
ds.m_MinThroughDrill = FromMM(0.2)
ds.m_CopperEdgeClearance = FromMM(0.3)
ns = ds.m_NetSettings
dflt = ns.GetDefaultNetclass()
dflt.SetClearance(FromMM(0.12)); dflt.SetTrackWidth(FromMM(0.127))
dflt.SetViaDiameter(FromMM(0.45)); dflt.SetViaDrill(FromMM(0.25))
pwr = pcbnew.NETCLASS("Power")
pwr.SetClearance(FromMM(0.12)); pwr.SetTrackWidth(FromMM(0.25))
pwr.SetViaDiameter(FromMM(0.45)); pwr.SetViaDrill(FromMM(0.25))
ns.SetNetclass("Power", pwr)
for n in ("/GND", "/+3V3", "/VBAT"):
    ns.SetNetclassPatternAssignment(n, "Power")

nets = {}
for n in sorted(set(pad_net.values())):
    ni = pcbnew.NETINFO_ITEM(board, n)
    board.Add(ni)
    nets[n] = ni

# ------------------------------------------------------------------ footprints
def load(fpid):
    lib, name = fpid.split(":")
    path = f"{PRJ}/disctracker.pretty" if lib == "disctracker" else f"{STD}{lib}.pretty"
    fp = pcbnew.FootprintLoad(path, name)
    fp.SetFPID(pcbnew.LIB_ID(lib, name))
    return fp

DNP = {"U4", "U5", "C7", "C8", "C9", "C10", "R7", "R8"}
FPS = {}
def place(ref, x, y, rot=0, back=False):
    c = comps[ref]
    fp = load(c["fp"])
    fp.SetReference(ref); fp.SetValue(c["value"])
    fp.SetPath(pcbnew.KIID_PATH("/" + c["uuid"]))
    fp.SetSheetname("Root"); fp.SetSheetfile(f"{NAME}.kicad_sch")
    board.Add(fp)
    fp.SetPosition(B(x, y))
    if back:
        fp.Flip(fp.GetPosition(), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
    fp.SetOrientationDegrees(rot)
    if ref in DNP:
        fp.SetDNP(True); fp.SetExcludedFromPosFiles(True)
    fp.SetExcludedFromBOM(ref.startswith("TP") or ref.startswith("H"))
    for p in fp.Pads():
        n = pad_net.get((ref, p.GetNumber()))
        if n:
            p.SetNet(nets[n])
    r = fp.Reference()   # designators go on the fab layer; the board is too dense for silk refs
    r.SetLayer(pcbnew.B_Fab if back else pcbnew.F_Fab)
    r.SetTextSize(VECTOR2I(FromMM(0.5), FromMM(0.5))); r.SetTextThickness(FromMM(0.08))
    FPS[ref] = fp
    return fp

# Motion sensors (sensor face, all identical orientation) + their local parts
IMU = {"U1": (0, 0), "U2": (20, 0), "U3": (-20, 0), "U4": (0, 20), "U5": (0, -20)}
for i, (u, (x, y)) in enumerate(IMU.items()):
    place(u, x, y)
    if u == "U5":   # next to the magnetometer: caps go beside the chip to free space below it
        place(f"C{2*i+1}", x + 2.7, y - 0.6, 90)
        place(f"C{2*i+2}", x - 2.7, y - 0.6, 90)
    else:
        place(f"C{2*i+1}", x + 1.3, y - 2.5)    # VDD (pin 8) decoupling
        place(f"C{2*i+2}", x - 1.3, y - 2.5)    # VDDIO (pin 5) decoupling
    place(f"R{4+i}", x, y + 2.5)                # CS pull-up, next to pin 12

# GND fan-out for every IMU, placed before autorouting and locked so the router keeps it:
# pins 2+3 (SDx/SCx) joined and taken to a via up-left; pins 6+7 joined and taken to a via below.
def track(x1, y1, x2, y2, net, w=0.15, layer=pcbnew.F_Cu):
    t = pcbnew.PCB_TRACK(board)
    t.SetStart(B(x1, y1)); t.SetEnd(B(x2, y2)); t.SetWidth(FromMM(w)); t.SetLayer(layer)
    t.SetNet(nets[net]); t.SetLocked(True); board.Add(t)

def via(x, y, net):
    v = pcbnew.PCB_VIA(board)
    v.SetPosition(B(x, y)); v.SetWidth(FromMM(0.45)); v.SetDrill(FromMM(0.25))
    v.SetNet(nets[net]); v.SetLocked(True); board.Add(v)

for u, (x, y) in IMU.items():
    # math coords: pin2 (-1.163, +0.25), pin3 (-1.163, -0.25), pin6 (0, -0.912), pin7 (0.5, -0.912)
    track(x - 1.163, y + 0.25, x - 1.163, y - 0.25, "/GND")
    track(x - 1.163, y, x - 2.3, y + 0.9, "/GND")
    via(x - 2.3, y + 0.9, "/GND")
    track(x, y - 0.912, x + 0.5, y - 0.912, "/GND")
    if u == "U2":   # the XIAO's underside SWD pads sit right below U2: jog the via left
        track(x, y - 0.912, x, y - 1.45, "/GND")
        track(x, y - 1.45, x - 0.9, y - 1.9, "/GND")
        via(x - 0.9, y - 1.9, "/GND")
    else:
        track(x, y - 0.912, x, y - 1.75, "/GND")
        via(x, y - 1.75, "/GND")

# Magnetometer
U6 = (0.0, -25.0)
place("U6", *U6)
place("C11", U6[0] - 2.0, U6[1], 90)
place("R1", U6[0] + 2.45, U6[1] + 0.8)
place("R2", U6[0] + 2.45, U6[1] - 0.8)

# XIAO on the back, center (+15, 0), USB-C pointing +X
XC = (15.0, 0.0)
def xiao_frame(fp):
    pads = {p.GetNumber(): M(p.GetPosition()) for p in fp.Pads()}
    c = [sum(pads[k][i] for k in ("1", "7", "8", "14")) / 4 for i in (0, 1)]
    usb = [(pads["1"][i] + pads["14"][i]) / 2 - c[i] for i in (0, 1)]
    return c, usb
m1 = place("M1", *XC, back=True)
for rot in (0, 90, 180, 270):
    m1.SetOrientationDegrees(rot)
    c, usb = xiao_frame(m1)
    if usb[0] > 5:
        break
m1.SetPosition(m1.GetPosition() + B(XC[0] - c[0], XC[1] - c[1]) - B(0, 0))
c, usb = xiao_frame(m1)
assert abs(c[0] - XC[0]) < 0.01 and usb[0] > 5, (c, usb)
xp = {p.GetNumber(): M(p.GetPosition()) for p in m1.Pads()}
for g in m1.GraphicalItems():   # XIAO outline would hang over the USB-C flat: keep it on fab only
    if g.GetLayer() == pcbnew.B_SilkS and g.GetClass() == "PCB_SHAPE":
        g.SetLayer(pcbnew.B_Fab)

def out(pad, d):  # point d mm outside the XIAO next to a castellated pad
    x, y = xp[pad]
    return x, y + (d if y > 0 else -d)

place("C12", *out("12", 3.0), 90, back=True)          # bulk at 3V3 pin, XIAO face
place("R3", *out("9", 3.0), 90)                        # SPI clock series, sensor face
jx, jy = out("7", 3.4)
place("JP1", jx, jy, 0)
place("R9", jx, jy + (2.4 if jy > 0 else -2.4), 0)

# Buzzer, battery pads, trim pads (XIAO face)
place("BZ1", 0, 21.5, 0, back=True)
place("J1", -18.4, 3.0, 0, back=True)
place("J2", -18.4, -3.0, 0, back=True)
for ref, a in (("TP1", 45), ("TP2", 135), ("TP3", 225), ("TP4", 315)):
    place(ref, 22 * math.cos(math.radians(a)), 22 * math.sin(math.radians(a)), back=True)
for ref, a in (("H1", 30), ("H2", 150), ("H3", 250)):
    place(ref, 25.6 * math.cos(math.radians(a)), 25.6 * math.sin(math.radians(a)))

# ------------------------------------------------------------------ outline
L = lambda n: board.GetLayerID(n)
yf = math.sqrt(R_BOARD**2 - FLAT_X**2)
arc = pcbnew.PCB_SHAPE(board, pcbnew.SHAPE_T_ARC)
arc.SetArcGeometry(B(FLAT_X, yf), B(-R_BOARD, 0), B(FLAT_X, -yf))
arc.SetLayer(pcbnew.Edge_Cuts); arc.SetWidth(FromMM(0.1)); board.Add(arc)
seg = pcbnew.PCB_SHAPE(board, pcbnew.SHAPE_T_SEGMENT)
seg.SetStart(B(FLAT_X, -yf)); seg.SetEnd(B(FLAT_X, yf))
seg.SetLayer(pcbnew.Edge_Cuts); seg.SetWidth(FromMM(0.1)); board.Add(seg)

def poly_zone(layer, pts, net=None, rule=False, prio=0, name=""):
    z = pcbnew.ZONE(board)
    z.SetLayer(layer)
    o = z.Outline(); o.NewOutline()
    for x, y in pts:
        o.Append(FromMM(OX + x), FromMM(OY - y))
    if rule:
        z.SetIsRuleArea(True)
        z.SetDoNotAllowTracks(True); z.SetDoNotAllowVias(False); z.SetDoNotAllowPads(False)
        z.SetDoNotAllowCopperPour(False); z.SetDoNotAllowFootprints(name == "battery")
        z.SetZoneName(name)
    else:
        z.SetNet(net); z.SetAssignedPriority(prio)
        z.SetLocalClearance(FromMM(0.2)); z.SetMinThickness(FromMM(0.2))
        z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
        z.SetThermalReliefGap(FromMM(0.2)); z.SetThermalReliefSpokeWidth(FromMM(0.25))
    board.Add(z)
    return z

SQ = [(-30, 30), (30, 30), (30, -30), (-30, -30)]
poly_zone(pcbnew.In1_Cu, SQ, nets["/GND"])
poly_zone(pcbnew.In2_Cu, SQ, nets["/+3V3"])
# outer-layer GND pours are added by route.py after autorouting

# B.Cu under the XIAO body: no tracks (only its own pads) - vias are tented and allowed
xs = sorted(v[0] for v in xp.values()); ys = sorted(v[1] for v in xp.values())
poly_zone(pcbnew.B_Cu, [(XC[0] - 10.0, 6.4), (XC[0] + 10.0, 6.4), (XC[0] + 10.0, -6.4), (XC[0] - 10.0, -6.4)],
          rule=True, name="under XIAO")
# Battery footprint on the XIAO face: no parts there
BAT = (-6.54, 0.0, 19.75, 26.02)
bx0, bx1 = BAT[0] - BAT[2] / 2, BAT[0] + BAT[2] / 2
by0, by1 = BAT[1] - BAT[3] / 2, BAT[1] + BAT[3] / 2
z = poly_zone(pcbnew.B_Cu, [(bx0, by1), (bx1, by1), (bx1, by0), (bx0, by0)], rule=True, name="battery")
z.SetDoNotAllowTracks(False)

# ------------------------------------------------------------------ silkscreen / fab
def text(s, x, y, layer, size=1.0, rot=0, mirror=False, bold=False):
    t = pcbnew.PCB_TEXT(board)
    t.SetText(s); t.SetPosition(B(x, y)); t.SetLayer(layer)
    t.SetTextSize(VECTOR2I(FromMM(size), FromMM(size))); t.SetTextThickness(FromMM(size * 0.15))
    t.SetTextAngleDegrees(rot); t.SetMirrored(mirror); t.SetBold(bold)
    board.Add(t)

def line(x1, y1, x2, y2, layer, w=0.15):
    s = pcbnew.PCB_SHAPE(board, pcbnew.SHAPE_T_SEGMENT)
    s.SetStart(B(x1, y1)); s.SetEnd(B(x2, y2)); s.SetLayer(layer); s.SetWidth(FromMM(w))
    board.Add(s)

def rect(x0, y0, x1, y1, layer, w=0.15):
    for a, b, c, d in ((x0, y0, x1, y0), (x1, y0, x1, y1), (x1, y1, x0, y1), (x0, y1, x0, y0)):
        line(a, b, c, d, layer, w)

F, BS = pcbnew.F_SilkS, pcbnew.B_SilkS
text("DiscTracker 0.1", -10, -8.5, F, 1.0)
text("FRONT", 23.2, 0, F, 1.0, 90)
for lab, (x, y) in (("A+", (20, 3.6)), ("A-", (-20, 3.6)), ("B+", (3.6, 20)), ("B-", (-4.4, -20))):
    text(lab, x, y, F, 0.8)
for a in (0, 90, 180, 270):  # edge ticks marking the X / Y axes
    c, s = math.cos(math.radians(a)), math.sin(math.radians(a))
    if a == 0:
        continue
    line(26.6 * c, 26.6 * s, 27.4 * c, 27.4 * s, F, 0.2)
rect(bx0, by0, bx1, by1, BS)
text("BATTERY  Adafruit 1317", BAT[0], 1.2, BS, 1.0, 90, mirror=True)
text("+", -18.4, 6.0, BS, 1.2, mirror=True)
text("-", -18.4, -6.0, BS, 1.2, mirror=True)
text("XIAO  USB-C ->", XC[0], -10.6, BS, 0.9, mirror=True)

pcbnew.SaveBoard(f"{PRJ}/{NAME}.kicad_pcb", board)
print("placed", len(FPS), "footprints; XIAO pads 7/9/12 at", xp["7"], xp["9"], xp["12"])
