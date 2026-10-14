#!/usr/bin/env python3
"""DiscTracker housing, rev C (CadQuery): twist-lock pod, glued dock, dock-gluing jig.

usage: python housing.py [out_dir] [--process fdm|mjf] [--fit-adjust MM] [--xiao-step PATH]

  --process     fdm (default): Bambu P1S, PETG, 0.4 mm nozzle, no supports. mjf: JLC3DP PA11.
  --fit-adjust  added to every sliding fit after a test print (+0.05 looser, -0.05 tighter).
  --xiao-step   also checks the parts against Seeed's XIAO nRF52840 STEP model (not redistributed here).

Writes STEP (for SolidWorks) and STL (for printing) per part, an assembly STEP, and report.json with
every fit, gap, stack-up, force, torque, strain and mass.

Frame (same as the PCB): origin on the spin axis, +X toward the XIAO's USB-C flat, +Y up as seen from the
sensor face. +Z points toward the disc's flight plate; z = 0 is the plate underside, which the pod's lid
touches. Angles are about +Z. All dimensions in mm.

How it fits together
  pod    lid + wall around the board, a flat with the USB-C port. Three lugs flush with the lid, three short
         ratchet racks on the wall, grip ribs below the dock. Board, XIAO and battery inside.
  cover  closes the bottom: reset access, LED window with a light shroud, the buzzer's front chamber.
         3 x M2 countersunk screws from the lid side pass through the board's alignment holes into the
         cover's columns and clamp the board between the lid bosses and the columns.
  dock   ring glued under the disc. The pod goes in with its lugs through three notches (the wide lug keys
         it one way round) and turns 30 deg clockwise as seen from below. The lugs ride up ramps on the
         dock's lip and pull the lid tight against the plate; three spring pawls click over the racks and
         stop it unscrewing. To remove: turn it back (it clicks out) and pull.
  jig    frame that self-centres on the disc rim + sliding plunger whose keys carry the dock to the plate.

Strength comes from the lugs sitting over a solid lip, not from anything that bends, so print tolerances
change how far it turns, not how well it holds. The pod, cover and dock print flat with no supports.
"""
import json, math, os, sys
import cadquery as cq

HERE = os.path.dirname(os.path.abspath(__file__))
args = [a for a in sys.argv[1:]]


def _opt(name, default=None):
    if name in args:
        i = args.index(name); v = args[i + 1]; del args[i:i + 2]
        return v
    return default


XIAO_STEP = _opt("--xiao-step")
PROCESS = _opt("--process", "fdm")
FIT_ADJ = float(_opt("--fit-adjust", "0"))
OUT = args[0] if args else os.path.join(HERE, "out")
BOARD = json.load(open(os.path.join(HERE, "board_parts.json")))
assert PROCESS in ("fdm", "mjf"), PROCESS

# =============================================================== process, material and fit classes
if PROCESS == "fdm":
    MATERIAL = "PETG (FDM: Bambu P1S, 0.4 mm nozzle)"
    E_MOD = 1900.0               # MPa, printed PETG bent along its layers
    EPS_ALLOW = 1.5              # %, repeated bending along the layers (about 1/3 of PETG's yield strain)
    SIG_XY, SIG_Z = 40.0, 15.0   # MPa, design strength along / across the layers (PETG ~50 / ~20-30)
    DENSITY = 1.27               # g/cm3, solid (4 walls + 100 % infill)
    MU = 0.35                    # PETG on PETG
    REVEAL = 0.30                # cover to wall: FDM outer walls run ~0.1 over, holes ~0.1 under
    PILOT_D = 1.7                # M2 thread-forming into PETG
    ARM_T = 1.5                  # ratchet arm thickness
else:
    MATERIAL = "PA11-HP (MJF, JLC3DP)"
    E_MOD = 1800.0
    EPS_ALLOW = 6.7              # %, 1/3 of Z elongation at yield (HP snap-fit handbook)
    SIG_XY, SIG_Z = 40.0, 40.0   # MJF is nearly isotropic
    DENSITY = 1.05
    MU = 0.30
    REVEAL = 0.30
    PILOT_D = 1.6
    ARM_T = 1.7                  # PA11 is softer than PETG; it takes the extra strain easily
TOL = 0.10                       # +/- per printed feature (radius or height) in the stack-ups; rerun at 0.2 too
C_LOC = 0.30 + FIT_ADJ           # radial / side clearance of every sliding fit (lip bore, groove, notches)
C_BOARD = 0.40                   # board edge to pod wall: the screws locate the board, never the wall
C_MOVE = 0.60                    # gaps around flexures: 1.5 line widths, so they never fuse
MIN_GAP = 0.40                   # smallest gap a 0.4 nozzle keeps open

# =============================================================== board and parts
BOARD_R, BOARD_FLAT_X, BOARD_T = BOARD["board_r"], BOARD["flat_x"], BOARD["thickness"]
HOLES = [(h["x"], h["y"]) for h in BOARD["holes"]]
TOP_PARTS_H = max(p["h"] for p in BOARD["parts"] if p["side"] == "sensor")   # 0.86 LGA-14
# XIAO nRF52840 Sense, from Seeed's STEP model mapped into this frame (X = 15 + x_step - 1.8045, Y = z_step + 6.111)
XIAO_C, XIAO_L, XIAO_W = (15.0, 0.0), 20.955, 17.78
XIAO_T = 1.25                    # XIAO PCB: Seeed STEP 1.25; users measure 1.17-1.27 (Seeed publishes none)
SOLDER = 0.05                    # castellated joint
USB_X, USB_HW, USB_H = (19.70, 27.00), 4.47, 3.21      # receptacle shell (front face at X 27.0)
SW_X, SW_Y = (22.30, 24.90), (-6.52, -4.92)
SW_H, SW_H_TOL = 0.62, 0.10                            # reset: 2.6x1.6x0.53 part (EVPBB2A9-class) + solder .. STEP model 0.73
SW_TRAVEL, SW_FORCE = 0.11, 1.6                        # mm, N (EVPBB2A9)
LEDS = [((22.19, 23.19), (5.20, 6.21)), ((24.53, 25.16), (5.07, 6.34))]   # RGB, CHG (red)
LED_H = 0.30
SHIELD_X, SHIELD_HW, SHIELD_H = (7.94, 18.54), 6.30, 2.0
MIC = ((4.75, 7.40), (2.84, 6.34), 0.94)
IC33 = ((4.80, 6.40), (-3.41, -0.21), 0.50)
BAT_C, BAT_X, BAT_Y, BAT_T = (-6.54, 0.0), 19.75, 26.02, 3.8   # Adafruit 1317
BAT_TAPE, BAT_SWELL = 0.10, 0.40
BUZ_C, BUZ_S, BUZ_T = (0.0, 21.5), 9.0, 1.9                   # CUI CPT-9019S, +/-0.5 body, Ø0.5 port in a corner
TRIM_H = 2.0                     # solder you may add on the TP1-TP4 balance pads

# =============================================================== Z stack (z = 0 at the plate underside)
LID_T = 1.0
CLR_TOP = 0.30                   # lid to the tallest sensor-face part (covers lid flatness and board bow)
Z_BT = -(LID_T + CLR_TOP + TOP_PARTS_H)        # board top            -2.16
Z_BB = Z_BT - BOARD_T                           # board bottom         -2.96
Z_XT = Z_BB - SOLDER - XIAO_T                   # XIAO component face  -4.26
XIAO_ENV = SOLDER + XIAO_T + USB_H              # 4.51
BAT_ENV = BAT_TAPE + BAT_T + BAT_SWELL          # 4.30
BOT_ENV = max(XIAO_ENV, BAT_ENV, TRIM_H)
CLR_BOT = 0.25                   # cover to the USB-C shell
Z_CI = Z_BB - BOT_ENV - CLR_BOT                 # cover inner face     -7.72
COVER_T = 1.0
Z_BOT = Z_CI - COVER_T                          # pod bottom           -8.72
Z_USB = Z_XT - USB_H / 2                        # USB-C centre         -5.865
Z_USB_BOT = Z_XT - USB_H                        # shell face toward the cover -7.47
Z_SW = Z_XT - SW_H                              # reset switch top
Z_BF = Z_BB - BUZ_T                             # buzzer face

# =============================================================== pod
R_IN = BOARD_R + C_BOARD                        # 28.4
WALL = 1.0
R_OUT = R_IN + WALL                             # 29.4
X_FIN = BOARD_FLAT_X + C_BOARD                  # 26.9 inner flat
X_FOUT = X_FIN + WALL                           # 27.9 outer flat
CH_BOT = 0.4                                    # bottom outer chamfer
CH_TOP = 0.4                                    # lid edge chamfer: lies on the print bed, takes the elephant's foot
# twist-lock lugs, flush with the lid (printed on the bed). Locked angles; they go in TWIST deg earlier.
R_LUG = R_OUT + 2.2                             # 31.6
Z_LUG_BOT = -1.8
LUGS = [(22.5, 24.0), (142.5, 16.0), (262.5, 16.0)]   # (centre, width) deg. Only the wide lug fits the wide notch: one way in
TWIST = 30.0                                    # clockwise seen from below (+ about +Z), like a jar lid
# ratchet racks on the wall at the lip's height, one per dock pawl. Valleys sit on the pawls when locked.
RACK_H, RACK_PITCH, RACK_N = 0.60, 3.0, 7       # tooth height, pitch (deg), teeth: big enough to print crisply
RACK_LEAD, RACK_HOLD = 30.0, 55.0               # flank angles from the tangent: tightening side, holding side
Z_RACK = (-4.65, -2.45)
# grip ribs on the wall below the dock, for turning the pod with wet or cold fingers
RIB_H, RIB_W, RIB_PITCH, RIB_FLAT = 0.40, 1.2, 7.5, 25.0
# M2 x 6 countersunk screws (nylon or brass - nothing magnetic near the magnetometer)
SCREW_CLR, CSK_D = 2.3, 4.1
BOSS_R = 2.3
LID_POSTS = [(11.0, 7.0), (-11.0, 7.0), (11.0, -7.0), (-11.0, -7.0)]   # rest on bare board, clear of parts
POST_GAP = 0.05
# USB-C: full-depth opening for the plug's overmold (Apple accessory guideline >= 12.45 x 6.60, full radius,
# plus 0.25 per side for print and XIAO position). The receptacle face sits 0.8 behind the outer flat.
USB_OPEN_W, USB_OPEN_H = 13.10, 7.20
BEZEL_T, BEZEL_C = 1.0, 0.30                    # cover posts beside the receptacle (close the side gaps)
TEXT = "DISCTRACKER"

# =============================================================== cover
R_COV = R_IN - REVEAL
X_COV = X_FIN - REVEAL
CH_COV = 0.4
COL_R = 1.9
PILOT_DEPTH = 3.6                               # M2 x 6 thread-forming: 3 mm of thread (shallow enough to depowder MJF)
RESET = "pin" if PROCESS == "fdm" else "tongue" # FDM: pinhole (the tongue's spring arm would be an overhang); MJF: press ring
PIN_D = 1.6                                     # pinhole for a paperclip, countersunk outside
# reset flexure: tongue (main spring) + springboard plunger (force limiter); the tongue's strip under the
# USB-C shell is the hard stop, so the stop and the switch share one reference (the XIAO) and a hard press
# goes into the shell, not the switch
TONGUE_X, TONGUE_Y = (11.5, 24.6), (-7.6, -2.9)
STRIP_X, STRIP_Y0 = (19.4, -4.67)               # strip under the shell: x from 19.4 to the tip, y from -4.67 up
SW_C = ((SW_X[0] + SW_X[1]) / 2, (SW_Y[0] + SW_Y[1]) / 2)          # (23.60, -5.72)
SB_X, SB_HW, SB_T, SB_GAP = (19.0, 19.8, 24.3), 1.0, 0.90, 0.80     # root block x0..x1, tip; half width; beam; gap below
SB_COL_X0 = 17.4                                # anchor column reaches under the shield (0.66 below it) for a stiff root
S_PRE = 0.20                                    # plunger to switch at rest (worst case still < 1.6 N, never held in reset)
X_SB_NOM = 0.32                                 # springboard deflection at the stop -> ~3.8 N on the switch (actuates at 1.6 N +/- 30 %)
G_PLUNGER = S_PRE + SW_TRAVEL + X_SB_NOM        # tongue travel at the plunger when the stop lands
TIP_RATIO = 1.08                                # tongue deflection at the tip / at the plunger (tip load)
G_STOP = G_PLUNGER * TIP_RATIO                  # strip-to-shell gap at the tip
# LED window + light shroud, buzzer chamber + outlets
LED_SLOT = ((21.90, 25.45), 5.70, 1.70)
SHROUD_T, SHROUD_GAP = 0.8, 0.40
BUZ_IN, BUZ_WALL, BUZ_GAP = 4.9, 0.8, 0.30
BUZ_HOLES = [(-1.6, 21.5), (1.6, 21.5)]
BUZ_HOLE_D = 1.6
BAT_RIB_T, BAT_RIB_C, BAT_RIB_UP = 0.8, 0.5, 0.8

# =============================================================== dock (printed lip-down, glue face up)
T_GLUE = 0.25                                   # VHB 4914-025 (0.25) or 9495LE (0.17); the ramps take the difference
Z_DTOP = -T_GLUE
R_LIP_IN = R_OUT + C_LOC                        # 29.7 lip bore: centres the pod
R_GROOVE = R_LUG + C_LOC                        # 31.9 wall around the lugs
R_D_OUT = R_GROOVE + 2.6                        # 34.5 (69 mm, as rev B): tape face 2.6 wide
Z_LIP = Z_LUG_BOT - 0.40                        # lip top: 0.4 under the lugs while they turn
Z_DOCK_BOT = -4.85
NOTCH_C = C_LOC + 0.30                          # lug to notch side, per side: easy to find by feel
# helical ramp under each lug's leading edge: the lug meets it mid-way at nominal, +/-0.3 mm of Z
# tolerance moves the lock angle +/-6 deg. Then a short dwell and a hard end stop.
RAMP_H, RAMP_A = 0.80, 16.0
DWELL_A, STOP_A = 2.0, 3.0
PHI_MAX = RAMP_A / 2 + DWELL_A                  # furthest the pod can turn past nominal
# ratchet: in-plane cantilever arms in the lip (they bend along the layers), one pawl at each tip
PAWLS = [97.5, 217.5, 331.0]                    # pawl angles, deg (clear of the ramps, notches and the USB-C notch)
R_REL = R_OUT + RACK_H + 0.30                   # 30.30 bore relief where the racks sweep
ARM_L, ARM_GAP = 11.0, 0.85                     # ratchet arm length to the pawl, slot behind it (= overtravel stop)
PAWL_H = 0.80                                   # tip at 29.50: 0.5 over the rack teeth
TIP_GAP = 0.80
USB_NOTCH_HW, Z_USB_NOTCH = 6.8, Z_LIP          # under the dock, room for a 12.35 x 6.5 mm USB-C overmold

# =============================================================== jig
DISC_OD = 211.0                                 # for the preview only; the cone fits 205-219 mm discs
RIM_DEPTH = 11.0                                # plate underside to rim bottom, preview only
SHAFT_R, JIG_CLR = 6.0, 0.25
CONE_R = (102.0, 110.0)
SPOKES = (90, 210, 330)
JIG_KEY_C = 0.30                                # plunger keys to the dock's notches, per side
JIG_RIDGE_H = 0.40                              # ridges the pawls grip, so the dock stays on the plunger


# =============================================================== helpers
def sector(pts, a0=0.0, a1=360.0):
    """revolve an (r, z) polygon about Z, counter-clockwise from a0 to a1 degrees"""
    s = cq.Workplane("XZ").polyline(pts).close().revolve(a1 - a0, (0, 0, 0), (0, 1, 0))
    return s.rotate((0, 0, 0), (0, 0, 1), a0) if a0 else s


def box(x0, x1, y0, y1, z0, z1):
    return cq.Workplane("XY").box(x1 - x0, y1 - y0, z1 - z0, centered=False).translate((x0, y0, z0))


def cyl(x, y, r, z0, z1):
    return cq.Workplane("XY").workplane(offset=z0).center(x, y).circle(r).extrude(z1 - z0)


def prism(pts, z0, z1):
    return cq.Workplane("XY").workplane(offset=z0).polyline(pts).close().extrude(z1 - z0)


def cone(x, y, r_top, r_bot, z_top, h):
    return cq.Workplane("XY").add(cq.Solid.makeCone(r_top, r_bot, h, cq.Vector(x, y, z_top), cq.Vector(0, 0, -1)))


def stadium_x(yc, zc, w, h, x0, x1):
    """stadium prism along +X, w along Y, h along Z"""
    return cq.Workplane("YZ").workplane(offset=x0).center(yc, zc).slot2D(w, h).extrude(x1 - x0)


def stadium_z(xc, yc, length, w, z0, z1, angle=0):
    return cq.Workplane("XY").workplane(offset=z0).center(xc, yc).slot2D(length, w, angle).extrude(z1 - z0)


def deg(mm, r):
    return math.degrees(mm / r)


def cant(b, t, L, d):
    """rectangular cantilever, tip load: stiffness N/mm, force N and root strain % at deflection d"""
    k = E_MOD * b * t ** 3 / (4 * L ** 3)
    return k, k * d, 150.0 * t * d / L ** 2


def tri_prism(theta, pts_ru, z0, z1):
    """prism along Z from points given as (radius, tangential offset) about the radial line at theta deg"""
    t = math.radians(theta)
    c, s = math.cos(t), math.sin(t)
    return prism([(r * c - u * s, r * s + u * c) for r, u in pts_ru], z0, z1)


def ramp(a0, a1, z0, z1, r0, r1, zb, n=8):
    """helical wedge on a lip: top rises linearly from z0 at a0 to z1 at a1 (deg), bottom flat at zb"""
    ws = []
    for k in range(n + 1):
        t = math.radians(a0 + (a1 - a0) * k / n)
        z = z0 + (z1 - z0) * k / n
        c, s = math.cos(t), math.sin(t)
        ws.append(cq.Wire.makePolygon([cq.Vector(r0 * c, r0 * s, zb), cq.Vector(r1 * c, r1 * s, zb),
                                       cq.Vector(r1 * c, r1 * s, z), cq.Vector(r0 * c, r0 * s, z)], close=True))
    return cq.Workplane("XY").add(cq.Solid.makeLoft(ws, True))


def fuse(lst):
    out = lst[0]
    for s in lst[1:]:
        out = out.union(s)
    return out


def chamfer_top(shape, z_top, r_base, h):
    """45 deg lead-in on the +Z end of features standing off a wall at r_base (also their print overhang)"""
    return shape.intersect(sector([(0, z_top - 30), (r_base + h + 2, z_top - 30), (r_base + h + 2, z_top - h - 2),
                                   (r_base, z_top), (0, z_top)]))


# =============================================================== pod
def lugs(phi=0.0, z0=Z_LUG_BOT, z1=0.0, r0=None):
    """the three lugs at a turn of phi deg from locked (phi = -TWIST: lined up with the notches)"""
    r0 = R_OUT - 0.3 if r0 is None else r0
    return fuse([sector([(r0, z0), (R_LUG, z0), (R_LUG, z1 - CH_TOP), (R_LUG - CH_TOP, z1), (r0, z1)],
                        a + phi - w / 2, a + phi + w / 2) for a, w in LUGS])


def rack_fit():
    """tooth phase (deg) that centres each pawl in a valley when locked, and the flank clearance there (mm)"""
    r_t, r_p = R_OUT + RACK_H, R_REL - PAWL_H
    e, rm = r_t - r_p, (r_t + r_p) / 2
    p = math.radians(RACK_PITCH) * rm
    a1, a2 = math.radians(RACK_LEAD), math.radians(RACK_HOLD)
    s = ((0.5 * p * math.tan(a1) - e) * math.cos(a1) - (0.5 * p * math.tan(a2) - e) * math.cos(a2)) / (math.sin(a1) + math.sin(a2))
    g = (math.tan(a1) * (0.5 * p - s) - e) * math.cos(a1)
    return deg(s, rm), g


def racks(phi=0.0):
    """sawtooth racks; the tightening flank leads (+theta), valleys centred on the pawls when locked"""
    tl, th = math.tan(math.radians(RACK_LEAD)), math.tan(math.radians(RACK_HOLD))
    hb = RACK_H + 0.1
    ph = rack_fit()[0]
    teeth = [tri_prism(ap + phi + ph + (k + 0.5) * RACK_PITCH, [(R_OUT - 0.1, -hb / th), (R_OUT + RACK_H, 0), (R_OUT - 0.1, hb / tl)],
                       Z_RACK[0], Z_RACK[1]) for ap in PAWLS for k in range(-4, RACK_N - 4)]
    return chamfer_top(fuse(teeth), Z_RACK[1], R_OUT, RACK_H)


def grip_ribs():
    z0, z1 = Z_BOT + CH_BOT + 0.3, Z_DOCK_BOT - 0.4
    n = int((360 - 2 * RIB_FLAT) / RIB_PITCH) + 1
    ribs = [tri_prism(RIB_FLAT + i * RIB_PITCH, [(R_OUT - 0.1, -RIB_W / 2), (R_OUT + RIB_H, -RIB_W / 2 + 0.25),
                                                 (R_OUT + RIB_H, RIB_W / 2 - 0.25), (R_OUT - 0.1, RIB_W / 2)], z0, z1)
            for i in range(n)]
    return chamfer_top(fuse(ribs), z1, R_OUT, RIB_H)


def pod(phi=0.0):
    prof = [(0, 0), (R_OUT - CH_TOP, 0), (R_OUT, -CH_TOP), (R_OUT, Z_BOT + CH_BOT), (R_OUT - CH_BOT, Z_BOT), (0, Z_BOT)]
    p = sector(prof)
    p = p.cut(box(X_FOUT, 40, -40, 40, Z_BOT - 1, 1))                          # USB-C flat
    yv = math.sqrt(R_OUT ** 2 - X_FOUT ** 2)
    try:
        p = p.edges(cq.selectors.BoxSelector((X_FOUT - 0.05, -yv - 0.05, Z_BOT), (X_FOUT + 0.05, yv + 0.05, -CH_TOP))).edges("|Z").fillet(0.8)
    except Exception:
        pass
    cav = cyl(0, 0, R_IN, Z_BOT - 1, -LID_T).cut(box(X_FIN, 40, -40, 40, Z_BOT - 2, 1))
    p = p.cut(cav)
    p = p.cut(sector([(R_IN - 0.01, Z_BOT - 0.01), (R_IN + 0.25, Z_BOT - 0.01), (R_IN - 0.01, Z_BOT + 0.25)]))  # reveal chamfer
    # screw bosses (board datum) and anti-sag posts under the lid
    for hx, hy in HOLES:
        p = p.union(cyl(hx, hy, BOSS_R, Z_BT, -LID_T + 0.01))
    for px, py in LID_POSTS:
        p = p.union(cyl(px, py, 0.9, Z_BT + POST_GAP, -LID_T + 0.01))
    for hx, hy in HOLES:
        p = p.cut(cyl(hx, hy, SCREW_CLR / 2, Z_BT - 1, 1))
        p = p.cut(cone(hx, hy, CSK_D / 2, SCREW_CLR / 2, 0.01, (CSK_D - SCREW_CLR) / 2 + 0.01))
    # USB-C: overmold opening through the flat, chamfered outside edge
    p = p.cut(stadium_x(0, Z_USB, USB_OPEN_W, USB_OPEN_H, X_FIN - 1, 40))
    p = p.cut(cq.Workplane("YZ").workplane(offset=X_FOUT + 0.01).center(0, Z_USB).slot2D(USB_OPEN_W + 0.8, USB_OPEN_H + 0.8)
              .workplane(offset=-0.41).slot2D(USB_OPEN_W, USB_OPEN_H).loft())
    p = p.union(lugs()).union(racks()).union(grip_ribs())
    # lid: name and a front mark pointing at the USB-C port (engraved 0.4)
    p = p.cut(cq.Workplane("XY").workplane(offset=-0.4).center(-1.5, -4.5)
              .text(TEXT, 4.6, 0.5, kind="bold", font="DejaVu Sans", halign="center", valign="center"))
    p = p.cut(prism([(18.5, -2.4), (18.5, 2.4), (22.5, 0)], -0.4, 0.1))
    return p.rotate((0, 0, 0), (0, 0, 1), phi) if phi else p


def test_ring():
    """top of the pod only (lugs, racks, wall): a 20-minute print to check the twist and the clicks"""
    return pod().intersect(cyl(0, 0, 40, -5.6, 1)).cut(cyl(0, 0, 26.0, -10, 2))


# =============================================================== cover
def cover():
    c = sector([(0, Z_BOT), (R_COV - CH_COV, Z_BOT), (R_COV, Z_BOT + CH_COV), (R_COV, Z_CI), (0, Z_CI)])
    c = c.cut(box(X_COV, 40, -40, 40, Z_BOT - 1, 1))
    c = c.edges(cq.selectors.BoxSelector((X_COV - 0.05, -30, Z_BOT - 0.05), (X_COV + 0.05, 30, Z_BOT + 0.05))).chamfer(CH_COV)
    if RESET == "tongue":
        # reset tongue: U slot (0.6) with round reliefs at the root; strip under the USB-C shell = stop
        (tx0, tx1), (ty0, ty1) = TONGUE_X, TONGUE_Y
        slot = box(tx0, tx1 + C_MOVE, ty0 - C_MOVE, ty1 + C_MOVE, Z_BOT - 1, Z_CI + 1).cut(box(tx0 - 1, tx1, ty0, ty1, Z_BOT - 2, Z_CI + 2))
        for y in (ty0 - C_MOVE / 2, ty1 + C_MOVE / 2):
            slot = slot.union(cyl(tx0, y, 0.45, Z_BOT - 1, Z_CI + 1))
        c = c.cut(slot)
        c = c.cut(box(STRIP_X, tx1 + 0.1, STRIP_Y0, ty1 + 0.1, Z_USB_BOT - G_STOP, Z_CI + 0.1))
        # springboard + plunger (force limiter)
        x0, x1, xt = SB_X
        yc = SW_C[1]
        c = c.union(box(SB_COL_X0, x1, yc - SB_HW, yc + SB_HW, Z_CI - 0.01, Z_CI + SB_GAP))
        c = c.union(box(x0, x1, yc - SB_HW, yc + SB_HW, Z_CI + SB_GAP - 0.01, Z_CI + SB_GAP + SB_T))
        c = c.union(box(x1 - 0.01, xt, yc - SB_HW, yc + SB_HW, Z_CI + SB_GAP, Z_CI + SB_GAP + SB_T))
        z_pt = Z_SW - S_PRE
        zb = Z_CI + SB_GAP + SB_T
        c = c.union(cq.Workplane("XY").add(cq.Solid.makeCone(1.0, 0.7, z_pt - zb, cq.Vector(SW_C[0], yc, zb - 0.01))))
    else:
        # pinhole over the reset switch (a paperclip reaches it 2.8 mm in), countersunk outside
        c = c.cut(cyl(SW_C[0], SW_C[1], PIN_D / 2, Z_BOT - 1, Z_CI + 1))
        c = c.cut(cone(SW_C[0], SW_C[1], PIN_D / 2, PIN_D / 2 + 0.5, Z_BOT + 0.5, 0.51))
    # columns (board clamp) with pilot holes for M2 thread-forming screws
    for hx, hy in HOLES:
        c = c.union(cyl(hx, hy, COL_R, Z_CI - 0.01, Z_BB))
        c = c.cut(cyl(hx, hy, PILOT_D / 2, Z_BB - PILOT_DEPTH, Z_BB + 1))
        c = c.cut(cone(hx, hy, PILOT_D / 2 + 0.3, PILOT_D / 2, Z_BB + 0.01, 0.31))
    # LED window + light shroud (open toward the USB-C shell)
    (lx0, lx1), ly, lw = LED_SLOT
    z_sh = Z_XT - LED_H - SHROUD_GAP
    sh = box(lx0 - SHROUD_T, lx1 + SHROUD_T, ly - lw / 2, ly + lw / 2 + SHROUD_T, Z_CI - 0.01, z_sh)
    sh = sh.cut(box(lx0, lx1, ly - lw / 2 - 1, ly + lw / 2, Z_CI - 1, z_sh + 1))
    c = c.union(sh)
    for sgn in (1, -1):                         # bezel posts beside the USB-C receptacle
        y0 = sgn * (USB_HW + BEZEL_C)
        c = c.union(box(X_COV - 0.8, X_COV, min(y0, y0 + sgn * BEZEL_T), max(y0, y0 + sgn * BEZEL_T), Z_CI - 0.01, Z_BB - 0.25))
    slot_led = stadium_z((lx0 + lx1) / 2, ly, lx1 - lx0, lw, Z_BOT - 1, Z_CI + 1)
    c = c.cut(slot_led)
    c = c.cut(cq.Workplane("XY").workplane(offset=Z_BOT - 0.01).center((lx0 + lx1) / 2, ly)
              .slot2D(lx1 - lx0 + 0.7, lw + 0.7).workplane(offset=0.36).slot2D(lx1 - lx0, lw).loft())
    # buzzer front chamber + two outlets (Helmholtz ~4 kHz)
    bx, by = BUZ_C
    z_ch = Z_BF - BUZ_GAP
    ch = box(bx - BUZ_IN - BUZ_WALL, bx + BUZ_IN + BUZ_WALL, by - BUZ_IN - BUZ_WALL, by + BUZ_IN + BUZ_WALL, Z_CI - 0.01, z_ch)
    ch = ch.cut(box(bx - BUZ_IN, bx + BUZ_IN, by - BUZ_IN, by + BUZ_IN, Z_CI - 1, z_ch + 1))
    c = c.union(ch)
    for hx, hy in BUZ_HOLES:
        c = c.cut(cyl(hx, hy, BUZ_HOLE_D / 2, Z_BOT - 1, Z_CI + 1))
        c = c.cut(cone(hx, hy, BUZ_HOLE_D / 2, BUZ_HOLE_D / 2 + 0.35, Z_BOT + 0.35, 0.36))
    # battery cage ribs (0.5 clear, 0.8 up the battery's sides); gaps at the wire pads and pack ends
    bx0, bx1 = BAT_C[0] - BAT_X / 2, BAT_C[0] + BAT_X / 2
    by1 = BAT_C[1] + BAT_Y / 2
    z_rt = Z_BB - BAT_TAPE - BAT_T + BAT_RIB_UP
    ribs = [box(bx0 - BAT_RIB_C - BAT_RIB_T, bx0 - BAT_RIB_C, 5.0, 11.0, Z_CI - 0.01, z_rt),
            box(bx0 - BAT_RIB_C - BAT_RIB_T, bx0 - BAT_RIB_C, -11.0, -5.0, Z_CI - 0.01, z_rt),
            box(bx1 + BAT_RIB_C, bx1 + BAT_RIB_C + BAT_RIB_T, -10.0, 10.0, Z_CI - 0.01, z_rt),
            box(-14.0, 1.0, by1 + BAT_RIB_C, by1 + BAT_RIB_C + BAT_RIB_T, Z_CI - 0.01, z_rt),
            box(-14.0, 1.0, -by1 - BAT_RIB_C - BAT_RIB_T, -by1 - BAT_RIB_C, Z_CI - 0.01, z_rt)]
    for r in ribs:
        c = c.union(r)
    # press mark on the tongue (engraved ring, 0.3 deep, clear of the thin stop strip)
    if RESET == "tongue":
        c = c.cut(cyl(22.6, -6.1, 1.4, Z_BOT - 0.1, Z_BOT + 0.3).cut(cyl(22.6, -6.1, 0.6, Z_BOT - 1, Z_BOT + 1)))
    return c


# =============================================================== dock
def rack_span():
    """angular extent of a rack about its pawl when locked (deg, -/+)"""
    hb = RACK_H + 0.1
    ph = rack_fit()[0]
    lo = ph + (-4 + 0.5) * RACK_PITCH - deg(hb / math.tan(math.radians(RACK_HOLD)), R_OUT)
    hi = ph + (RACK_N - 5 + 0.5) * RACK_PITCH + deg(hb / math.tan(math.radians(RACK_LEAD)), R_OUT)
    return lo, hi


def pawl_tip_deg():
    return deg((PAWL_H + 0.1) / math.tan(math.radians(RACK_HOLD)), R_REL)


def dock():
    zb, zt = Z_DOCK_BOT, Z_DTOP
    band = lambda r0, r1, z0, z1: [(r0, z0), (r1, z0), (r1, z1), (r0, z1)]
    d = sector([(R_LIP_IN + 0.4, zb), (R_D_OUT - 0.4, zb), (R_D_OUT, zb + 0.4), (R_D_OUT, zt - 0.3), (R_D_OUT - 0.3, zt),
                (R_GROOVE, zt), (R_GROOVE, Z_LIP), (R_LIP_IN, Z_LIP), (R_LIP_IN, zb + 0.4)])
    # under each lug's leading edge: helical ramp, dwell, end stop
    for a, w in LUGS:
        le = a + w / 2
        blk = ramp(le - RAMP_A / 2, le + RAMP_A / 2, Z_LIP, Z_LIP + RAMP_H, R_LIP_IN, R_GROOVE + 0.05, Z_LIP - 0.2)
        blk = blk.union(sector(band(R_LIP_IN, R_GROOVE + 0.05, Z_LIP - 0.2, Z_LIP + RAMP_H), le + RAMP_A / 2 - 0.1, le + PHI_MAX + 0.1))
        d = d.union(blk.union(sector(band(R_LIP_IN, R_GROOVE + 0.05, Z_LIP - 0.2, zt), le + PHI_MAX, le + PHI_MAX + STOP_A)))
    # notches the lugs go in through; the wide one keys the pod
    for a, w in LUGS:
        hw = w / 2 + deg(NOTCH_C, R_LUG)
        d = d.cut(sector(band(R_LIP_IN - 1, R_GROOVE + 0.01, zb - 1, Z_LIP + 0.01), a - TWIST - hw, a - TWIST + hw))
    # USB-C: room under the dock for the plug's overmold, so the pod charges in the disc
    d = d.cut(box(R_LIP_IN - 2, R_D_OUT + 1, -USB_NOTCH_HW, USB_NOTCH_HW, zb - 1, Z_USB_NOTCH))
    # ratchet: bore relief where each rack sweeps, a cantilever arm with a slot behind it, the pawl at its tip
    lo, hi = rack_span()
    rm = R_REL + ARM_T / 2
    for ap in PAWLS:
        d = d.cut(sector(band(R_LIP_IN - 1, R_REL, zb - 1, Z_LIP + 0.01), ap + lo - TWIST - 1, ap + hi + PHI_MAX + 1))
        a_root, a_end = ap - deg(ARM_L, rm), ap + pawl_tip_deg() + deg(0.1, R_REL)
        a_gap = a_end + deg(TIP_GAP, rm)
        r_s0, r_s1 = R_REL + ARM_T, R_REL + ARM_T + ARM_GAP
        d = d.cut(sector(band(r_s0, r_s1, zb - 1, Z_LIP + 0.01), a_root, a_gap))
        d = d.cut(sector(band(R_LIP_IN - 1, r_s1, zb - 1, Z_LIP + 0.01), a_end, a_gap))
        t = math.radians(a_root)
        rc = (r_s0 + r_s1) / 2
        d = d.cut(cyl(rc * math.cos(t), rc * math.sin(t), ARM_GAP / 2, zb - 1, Z_LIP + 0.01))      # round slot end at the root
        tl, th = math.tan(math.radians(RACK_LEAD)), math.tan(math.radians(RACK_HOLD))
        hb = PAWL_H + 0.1
        d = d.union(tri_prism(ap, [(R_REL + 0.1, -hb / tl), (R_REL - PAWL_H, 0), (R_REL + 0.1, hb / th)], zb, Z_LIP))
    return d


# =============================================================== jig
def jig_plunger():
    """plunger printed head-down. Keys sit in the dock's notches (one way round), ridges under the pawls hold
    the dock by friction; slide the dock on until its taped face is flush with the head"""
    zh = Z_DOCK_BOT - 1.6
    prof = [(0, 0), (R_OUT - 0.4, 0), (R_OUT, -0.4), (R_OUT, zh), (SHAFT_R + 2.0, zh), (SHAFT_R, zh - 2.0),
            (SHAFT_R, -62.0), (0, -62.0)]
    p = sector(prof)
    pocket = sector([(SHAFT_R + 2.5, -1.6), (R_OUT - 1.4, -1.6), (R_OUT - 1.4, zh - 1), (SHAFT_R + 2.5, zh - 1)])
    for a in (60, 180, 300):
        pocket = pocket.cut(box(0, 40, -0.75, 0.75, -20, 0).rotate((0, 0, 0), (0, 0, 1), a))
    p = p.cut(pocket)
    for a, w in LUGS:
        hw = w / 2 + deg(NOTCH_C - JIG_KEY_C, R_LUG)
        p = p.union(sector([(R_OUT - 0.3, Z_DOCK_BOT - 1.0), (R_LUG, Z_DOCK_BOT - 1.0), (R_LUG, -CH_TOP), (R_LUG - CH_TOP, 0),
                            (R_OUT - 0.3, 0)], a - TWIST - hw, a - TWIST + hw))
    ridges = fuse([tri_prism(ap, [(R_OUT - 0.1, -0.6), (R_OUT + JIG_RIDGE_H, -0.3), (R_OUT + JIG_RIDGE_H, 0.3), (R_OUT - 0.1, 0.6)],
                             Z_DOCK_BOT - 1.0, -0.6) for ap in PAWLS])
    return p.union(chamfer_top(ridges, -0.6, R_OUT, JIG_RIDGE_H))


def jig_frame():
    r_c = DISC_OD / 2 - 0.5                     # rim corner contact radius
    z_s = -RIM_DEPTH - (r_c - CONE_R[0])        # spoke face nearest the disc
    rs0, rs1 = SHAFT_R + JIG_CLR, SHAFT_R + JIG_CLR + 3.0
    f = sector([(rs0, z_s + 3.0), (rs1, z_s + 3.0), (rs1, z_s - 22.0), (rs0, z_s - 22.0)])
    f = f.union(sector([(rs0, z_s), (16.0, z_s), (16.0, z_s - 5.0), (rs0, z_s - 5.0)]))
    for a in SPOKES:
        sp = box(10.0, CONE_R[1] + 3.0, -4.0, 4.0, z_s - 5.0, z_s).rotate((0, 0, 0), (0, 0, 1), a)
        foot = sector([(CONE_R[0], z_s), (CONE_R[1], z_s + (CONE_R[1] - CONE_R[0])), (CONE_R[1] + 3.0, z_s + (CONE_R[1] - CONE_R[0])),
                       (CONE_R[1] + 3.0, z_s - 5.0), (CONE_R[0], z_s - 5.0)], a - 5, a + 5)
        f = f.union(sp).union(foot)
    return f


# =============================================================== reference models (not for manufacture)
def disc_model():
    """generic driver section for the preview: plate, rim, dome"""
    r_o = DISC_OD / 2
    prof = [(0, 0), (r_o - 22.0, 0), (r_o - 21.0, -RIM_DEPTH + 2.0), (r_o - 18.0, -RIM_DEPTH), (r_o - 3.0, -RIM_DEPTH),
            (r_o, -RIM_DEPTH + 3.0), (r_o, -1.0), (r_o - 6.0, 1.6), (r_o - 30.0, 2.8), (0, 3.6)]
    return sector(prof)


def board_models():
    """sensor board, XIAO (from Seeed's STEP dimensions), battery and the other parts, as named solids"""
    m = {}
    b = cyl(0, 0, BOARD_R, Z_BB, Z_BT).cut(box(BOARD_FLAT_X, 40, -40, 40, Z_BB - 1, 1))
    for hx, hy in HOLES:
        b = b.cut(cyl(hx, hy, 1.05, Z_BB - 1, 1))
    m["pcb"] = b
    for p in BOARD["parts"]:
        if p["dnp"]:
            continue
        (x0, x1), (y0, y1) = p["x"], p["y"]
        z0, z1 = (Z_BT, Z_BT + p["h"]) if p["side"] == "sensor" else (Z_BB - p["h"], Z_BB)
        m[p["ref"]] = box(x0, x1, y0, y1, z0, z1)
    xc = XIAO_C[0]
    m["XIAO pcb"] = box(xc - XIAO_L / 2, xc + XIAO_L / 2, -XIAO_W / 2, XIAO_W / 2, Z_XT, Z_BB - SOLDER)
    m["USB-C"] = stadium_x(0, Z_XT - USB_H / 2, 2 * USB_HW, USB_H, USB_X[0], USB_X[1])
    m["shield"] = box(SHIELD_X[0], SHIELD_X[1], -SHIELD_HW, SHIELD_HW, Z_XT - SHIELD_H, Z_XT)
    m["reset"] = box(SW_X[0], SW_X[1], SW_Y[0], SW_Y[1], Z_SW, Z_XT)
    for i, ((lx0, lx1), (ly0, ly1)) in enumerate(LEDS):
        m[("LED rgb", "LED chg")[i]] = box(lx0, lx1, ly0, ly1, Z_XT - LED_H, Z_XT)
    m["mic"] = box(MIC[0][0], MIC[0][1], MIC[1][0], MIC[1][1], Z_XT - MIC[2], Z_XT)
    m["IC"] = box(IC33[0][0], IC33[0][1], IC33[1][0], IC33[1][1], Z_XT - IC33[2], Z_XT)
    m["battery"] = box(BAT_C[0] - BAT_X / 2, BAT_C[0] + BAT_X / 2, -BAT_Y / 2, BAT_Y / 2, Z_BB - BAT_TAPE - BAT_T, Z_BB - BAT_TAPE)
    return m


def xiao_from_step(path):
    shp = cq.importers.importStep(path)
    return shp.rotate((0, 0, 0), (1, 0, 0), -90).translate((15 - 1.8045, 6.111, Z_BB - SOLDER - 0.25))


# =============================================================== analysis
def stackups(TOL=TOL):
    """worst-case (WC) and root-sum-square (RSS) checks of the fits that matter"""
    def rec(nom, contrib, need_min=None, need_max=None):
        wc = sum(abs(c) for c in contrib); rss = math.sqrt(sum(c * c for c in contrib))
        out = {"nominal": round(nom, 3), "wc": [round(nom - wc, 3), round(nom + wc, 3)],
               "rss": [round(nom - rss, 3), round(nom + rss, 3)]}
        if need_min is not None: out["need_min"] = need_min
        if need_max is not None: out["need_max"] = need_max
        lo_ok = need_min is None or nom - rss >= need_min
        hi_ok = need_max is None or nom + rss <= need_max
        out["ok_rss"] = lo_ok and hi_ok
        out["ok_wc"] = (need_min is None or nom - wc >= need_min) and (need_max is None or nom + wc <= need_max)
        return out
    s = {}
    s["board edge to pod wall (radial)"] = rec(C_BOARD, [TOL, 0.10, 0.075, 0.10], need_min=0.0)     # wall R, PCB route, screw in hole, boss position
    s["board flat to pod inner flat"] = rec(C_BOARD, [TOL, 0.10, 0.075, 0.10], need_min=0.0)
    s["lid to tallest sensor part"] = rec(CLR_TOP, [TOL, 0.04, 0.05, 0.10], need_min=0.0)           # boss height, part, lid flatness, board bow
    s["cover to USB-C shell"] = rec(CLR_BOT, [TOL, 0.05, 0.05, 0.03], need_min=0.0)                 # column, XIAO pcb, shell, solder
    s["cover to battery (after 0.4 swell)"] = rec(Z_BB - BAT_TAPE - BAT_T - BAT_SWELL - Z_CI, [TOL, 0.2, 0.05], need_min=0.0)
    s["cover to pod wall (reveal)"] = rec(REVEAL, [TOL, TOL], need_min=0.0)
    # twist-lock
    s["pod wall to dock lip bore (radial)"] = rec(R_LIP_IN - R_OUT, [TOL, TOL, 0.05], need_min=0.0)
    s["lug to groove wall (radial)"] = rec(R_GROOVE - R_LUG, [TOL, TOL, 0.05], need_min=0.0)
    s["lug to notch side (per side)"] = rec(NOTCH_C, [TOL, TOL, 0.05], need_min=0.0)
    s["lug over the lip while turning (Z)"] = rec(Z_LUG_BOT - Z_LIP, [TOL, TOL, 0.08], need_min=0.0)  # lug, dock height, tape
    s["lug overlap on the lip (radial, holds the pod)"] = rec(R_LUG - R_LIP_IN, [TOL, TOL, 0.10], need_min=1.0)
    s["lock angle on the ramp, deg past nominal"] = rec(0.0, [c * RAMP_A / RAMP_H for c in (TOL, TOL, 0.08)],
                                                        need_min=-RAMP_A / 2, need_max=PHI_MAX)
    eng = R_OUT + RACK_H - (R_REL - PAWL_H)
    s["rack tips to bore relief (radial)"] = rec(R_REL - R_OUT - RACK_H, [TOL, TOL, 0.05], need_min=0.0)
    s["pawl tip to pod wall (radial)"] = rec(R_REL - PAWL_H - R_OUT, [TOL, TOL, 0.05], need_min=-(ARM_GAP - eng))
    s["ratchet engagement (pawl over a tooth; 0.15 still clicks)"] = rec(eng, [TOL, TOL, 0.10], need_min=0.15, need_max=ARM_GAP)
    s["pawl flank clearance when locked"] = rec(rack_fit()[1], [0.05, 0.05], need_min=0.0)
    s["ratchet arm slot (same part, stays open)"] = rec(ARM_GAP, [0.05, 0.05], need_min=MIN_GAP)
    s["USB-C 12.35x6.5 overmold to dock notch (per side, Y)"] = rec(USB_NOTCH_HW - 12.35 / 2, [TOL, 0.10, 0.10], need_min=0.0)
    s["USB-C overmold top to dock notch (Z)"] = rec(Z_USB_NOTCH - (Z_USB + 6.5 / 2), [TOL, 0.05, 0.10, 0.08], need_min=0.0)
    s["USB-C 12.35x6.5 overmold to opening (per side, Y)"] = rec((USB_OPEN_W - 12.35) / 2, [TOL, 0.10, 0.075, 0.10], need_min=0.0)
    s["USB-C 12.35x6.5 overmold to opening (per side, Z)"] = rec((USB_OPEN_H - 6.50) / 2, [TOL, 0.05, 0.10, 0.05], need_min=0.0)
    s["USB-C receptacle to bezel posts"] = rec(BEZEL_C, [TOL, 0.10, 0.075], need_min=0.0)
    if RESET == "tongue":
        s["reset plunger to switch at rest (>-0.15 = <1.6 N, not actuated)"] = rec(S_PRE, [TOL, 0.05, 0.05, 0.03, SW_H_TOL], need_min=-0.15)
        k = cant(2 * SB_HW, SB_T, SW_C[0] - SB_X[1], 1)[0]
        s["reset switch force at the stop, N"] = rec(k * X_SB_NOM, [k * c for c in (SW_H_TOL, 0.07, 0.05)], need_min=1.3 * SW_FORCE, need_max=6.5)
    else:
        s["reset pinhole to USB-C shell (edge, Y)"] = rec(-SW_C[1] - PIN_D / 2 - USB_HW, [TOL, 0.10, 0.075], need_min=0.0)
    s["LED shroud to LEDs"] = rec(SHROUD_GAP, [TOL, 0.05, 0.05], need_min=0.0)
    s["buzzer chamber rim to buzzer"] = rec(BUZ_GAP, [TOL, 0.10, 0.05], need_min=0.0)
    return s


def mechanics():
    out = {}
    fa = lambda mu: math.degrees(math.atan(mu))
    mus = (MU - 0.10, MU, MU + 0.10)
    # ratchet: cantilever arms in the dock's lip, pawl at the tip, racks on the pod
    h = Z_LIP - Z_DOCK_BOT
    eng = R_OUT + RACK_H - (R_REL - PAWL_H)
    k, P, eps = cant(h, ARM_T, ARM_L, eng)
    r_c = R_OUT + RACK_H / 2
    n = len(PAWLS)
    tq = lambda face, mu, p=P: n * p * math.tan(math.radians(face + fa(mu))) * r_c / 1000.0
    out["ratchet"] = {"pawls": n, "arm_length": ARM_L, "arm_thickness": ARM_T, "arm_height": round(h, 2),
                      "stiffness_N_per_mm": round(k, 2), "engagement": round(eng, 2),
                      "pawl_force_N_min_nom_max": [round(cant(h, ARM_T, ARM_L, eng + d)[1], 2) for d in (-0.15, 0, 0.15)],
                      "strain_pct_at_engagement": round(eps, 2),
                      "strain_pct_at_overtravel_stop": round(cant(h, ARM_T, ARM_L, ARM_GAP)[2], 2),
                      "pitch_deg": RACK_PITCH, "teeth_per_rack": RACK_N,
                      "tighten_torque_per_click_Nm": round(tq(RACK_LEAD, MU), 3),
                      "hold_torque_Nm_mu_low_nom_high": [round(tq(RACK_HOLD, m), 3) for m in mus],
                      "play_if_preload_lost_mm": round(RACK_PITCH * RAMP_H / RAMP_A, 3)}
    # ramp clamp: lugs wedge up the helical ramps, the lid bears on the plate
    r_r = (R_LIP_IN + R_LUG) / 2
    alpha = math.degrees(math.atan(RAMP_H / (math.radians(RAMP_A) * r_r)))
    r_lid = 2 * R_OUT / 3                        # friction radius of the lid on the plate
    clamp = lambda T, mu: T * 1000 / (r_r * math.tan(math.radians(alpha + fa(mu))) + mu * r_lid)
    untwist = lambda F, mu: F * (r_r * math.tan(math.radians(fa(mu) - alpha)) + mu * r_lid) / 1000
    F4 = clamp(0.4, MU)
    out["ramp clamp"] = {"helix_deg": round(alpha, 2), "friction_angle_deg": round(fa(MU), 1),
                         "self_locking (helix < friction angle at low mu)": alpha < fa(MU - 0.10),
                         "clamp_N_for_twist_0.2_0.4_0.6_Nm": [round(clamp(T, MU), 1) for T in (0.2, 0.4, 0.6)],
                         "untwist_torque_from_clamp_Nm (after 0.4 N.m)": round(untwist(F4, MU), 3),
                         "lock_angle_deg_per_mm_of_Z": round(RAMP_A / RAMP_H, 1)}
    hold = tq(RACK_HOLD, MU) + untwist(F4, MU)
    out["torque check"] = {"tree_hit_spin_stop_Nm (2,500 rpm stopped in ~6 ms)": 0.35,
                           "hold_Nm (ratchet + clamp, 0.4 N.m twist)": round(hold, 2),
                           "hold_Nm (ratchet only, low friction)": round(tq(RACK_HOLD, MU - 0.10), 2),
                           "ok": tq(RACK_HOLD, MU - 0.10) >= 0.35}
    # pull-out (rim-down landing): rigid lugs over a solid lip, three load paths
    w_min = min(w for _, w in LUGS)
    lever = r_r - R_OUT
    F_lug = SIG_XY * math.radians(w_min) * R_OUT * Z_LUG_BOT ** 2 / 6 / lever
    lever2 = R_GROOVE - r_r
    F_lip = SIG_XY * math.radians(w_min) * R_GROOVE * h ** 2 / 6 / lever2
    wt = R_D_OUT - R_GROOVE
    bw = 2 * math.radians(w_min) * (R_GROOVE + R_D_OUT) / 2      # the lip spreads a lug's load over about twice its width
    ecc = (R_GROOVE + R_D_OUT) / 2 - r_r
    F_wall = SIG_Z / (1 / (bw * wt) + 6 * ecc / (bw * wt ** 2))
    per = min(F_lug, F_lip, F_wall)
    tape = math.pi * (R_D_OUT ** 2 - R_GROOVE ** 2)
    out["pull-out"] = {"per_lug_N": {"lug root (bending)": round(F_lug), "lip root (bending)": round(F_lip),
                                     "dock wall (tension across layers)": round(F_wall)},
                       "total_N (weakest path x 3)": round(3 * per),
                       "g_to_pull_out_a_20_g_pod": round(3 * per / (0.020 * 9.81)),
                       "tape_area_mm2": round(tape), "tape_N (VHB about 0.5 MPa)": round(0.5 * tape),
                       "note": "the tape is the weakest link; nothing in the lock relies on a flexure"}
    if RESET == "tongue":
        Lsb = SB_X[2] - SB_X[1] - (SB_X[2] - SW_C[0])
        ksb = cant(2 * SB_HW, SB_T, Lsb, 1)[0]
        xr = [X_SB_NOM - 0.15, X_SB_NOM, X_SB_NOM + 0.15]
        kt = cant(TONGUE_Y[1] - TONGUE_Y[0], COVER_T, SW_C[0] - TONGUE_X[0], 1)[0]
        out["reset"] = {"tongue_stiffness_N_per_mm": round(kt, 2), "springboard_stiffness_N_per_mm": round(ksb, 2),
                                "switch_force_at_stop_N_min_nom_max": [round(ksb * x, 2) for x in xr],
                                "switch_rated_N": SW_FORCE, "finger_force_at_stop_N": round(kt * G_PLUNGER + ksb * X_SB_NOM, 1),
                                "travel_to_stop_mm": round(G_PLUNGER, 2), "stop_strip_thickness": round(Z_USB_BOT - G_STOP - Z_BOT, 2),
                                "springboard_strain_pct_max": round(cant(2 * SB_HW, SB_T, Lsb, xr[2])[2], 2),
                                "tongue_strain_pct": round(cant(TONGUE_Y[1] - TONGUE_Y[0], COVER_T, SW_C[0] - TONGUE_X[0], G_PLUNGER)[2], 2),
                                "stop": "tongue strip lands on the USB-C shell; plunger and stop both reference the XIAO"}
    else:
        out["reset"] = {"type": "pinhole", "hole_d": PIN_D, "depth_to_switch_mm": round(Z_SW - Z_BOT, 2),
                        "tool": "paperclip, 0.8-1.2 mm wire"}
    vol = (2 * BUZ_IN) ** 2 * (Z_BF - Z_CI)
    area = len(BUZ_HOLES) * math.pi * (BUZ_HOLE_D / 2) ** 2
    leff = COVER_T + 0.85 * BUZ_HOLE_D
    out["buzzer chamber"] = {"volume_mm3": round(vol, 0), "outlet_area_mm2": round(area, 2),
                             "helmholtz_Hz": round(343000 / (2 * math.pi) * math.sqrt(area / (vol * leff)), -1),
                             "buzzer_resonance_Hz": 4000}
    return out


def report_shapes(parts, models):
    """interference volumes and minimum gaps between named solids"""
    inter = {}
    for pn, P in parts.items():
        for mn, M in models.items():
            try:
                v = P.intersect(M).val().Volume()
            except Exception:
                v = 0.0
            if v > 1e-3:
                inter[f"{pn} x {mn}"] = round(v, 4)
    return inter


def gap(a, b):
    return round(a.val().distance(b.val()), 3)


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    P, C, D = pod(), cover(), dock()
    JF, JP, TR = jig_frame(), jig_plunger(), test_ring()
    M = board_models()
    parts = (("pod", P), ("cover", C), ("dock", D), ("jig_frame", JF), ("jig_plunger", JP), ("test_ring", TR))
    for name, part in parts:
        sol = part.solids().vals()
        assert len(sol) == 1 and part.val().isValid(), f"{name}: {len(sol)} solids, valid={part.val().isValid()}"
    rep = {"rev": "C", "process": PROCESS, "material": MATERIAL, "fit_adjust_mm": FIT_ADJ,
           "depth_below_plate_mm": round(-Z_BOT, 2),
           "pod_mm": {"wall_od": 2 * R_OUT, "over_lugs": 2 * R_LUG, "flat_to_centre": X_FOUT},
           "dock_mm": {"od": 2 * R_D_OUT, "bore": 2 * R_LIP_IN, "height": round(Z_DTOP - Z_DOCK_BOT, 2), "lowest_point": Z_DOCK_BOT},
           "lock": {"twist_deg": TWIST, "direction": "clockwise seen from below (USB-C port from 11 to 12 o'clock)",
                    "lugs_locked_deg_width": LUGS, "pawls_deg": PAWLS, "furthest_turn_past_nominal_deg": PHI_MAX},
           "z_stack_mm": {"lid_top": 0, "lid_underside": -LID_T, "board_top": round(Z_BT, 3), "board_bottom": round(Z_BB, 3),
                          "xiao_face": round(Z_XT, 3), "usb_c_centre": round(Z_USB, 3), "cover_inner": round(Z_CI, 3),
                          "pod_bottom": round(Z_BOT, 3)},
           "mass_g": {}, "stackups": stackups(), "mechanics": mechanics(),
           "stackups_at_tol_0.2 (robustness)": {k: {"rss": v["rss"], "ok_rss": v["ok_rss"]} for k, v in stackups(0.2).items()}}
    rat = rep["mechanics"]["ratchet"]
    rep["strain_check_pct"] = {"worst_flexure (ratchet arm, each click)": rat["strain_pct_at_engagement"],
                               "at_overtravel_stop": rat["strain_pct_at_overtravel_stop"], "allowable": EPS_ALLOW,
                               "ok": rat["strain_pct_at_engagement"] <= EPS_ALLOW}
    rep["balance"] = {"note": "off-centre mass of each part; trim with solder on TP1-TP4 (r = 22 mm) after weighing"}
    for name, part in parts:
        vol = part.val().Volume() / 1000.0
        rep["mass_g"][name] = round(vol * DENSITY, 2)
        if name in ("pod", "cover", "dock"):
            cg = part.val().Center()
            rep["balance"][name] = {"cg_xy_mm": [round(cg.x, 3), round(cg.y, 3)],
                                    "g_mm": [round(vol * DENSITY * cg.x, 2), round(vol * DENSITY * cg.y, 2)]}
        cq.exporters.export(part, f"{OUT}/{name}.step")
        cq.exporters.export(part, f"{OUT}/{name}.stl", tolerance=0.01, angularTolerance=0.1)
    # reference models for the viewer
    ref = {"board": M["pcb"]}
    ref["parts"] = fuse([M[k] for k in M if k not in ("pcb", "battery") and not k.startswith(("XIAO", "USB", "shield", "reset", "LED", "mic", "IC"))])
    ref["xiao"] = fuse([M[k] for k in ("XIAO pcb", "USB-C", "shield", "reset", "LED rgb", "LED chg", "mic", "IC")])
    ref["battery"] = M["battery"]
    ref["disc"] = disc_model()
    for k, v in ref.items():
        cq.exporters.export(v, f"{OUT}/ref_{k}.stl", tolerance=0.02, angularTolerance=0.15)
    # interference: housing vs board models, housing parts with each other (locked, and at the insertion angle)
    housing = {"pod": P, "cover": C, "dock": D}
    inter = report_shapes(housing, M)
    def vol(a, b):
        try:
            return a.intersect(b).val().Volume()
        except Exception:
            return 0.0
    for a_, b_ in (("pod", "cover"), ("pod", "dock"), ("cover", "dock")):
        v = vol(housing[a_], housing[b_])
        if v > 1e-3:
            inter[f"{a_} x {b_}"] = round(v, 4)
    P_in = pod(-TWIST)
    v = vol(P_in, D)
    if v > 1e-3:
        inter["pod at insertion angle x dock"] = round(v, 4)
    rep["interference_mm3"] = inter
    rep["designed_contact_mm3 (plunger ridges on the dock's pawls)"] = round(vol(JP, D), 3)
    rep["min_gap_mm"] = {
        "lid to U1 (centre IMU)": gap(P, M["U1"]),
        "lid to U2": gap(P, M["U2"]),
        "pod wall to board edge": gap(P.intersect(box(-40, 40, -40, 40, Z_BB - 0.3, Z_BT - 0.01)), M["pcb"]),
        "cover to USB-C shell": gap(C, M["USB-C"]),
        "cover to battery": gap(C, M["battery"]),
        "cover to shield": gap(C, M["shield"]),
        "cover to reset switch": gap(C, M["reset"]),
        "LED shroud to LEDs": min(gap(C, M["LED rgb"]), gap(C, M["LED chg"])),
        "buzzer chamber to buzzer": gap(C, M["BZ1"]),
        "pod to dock, locked (lugs on the ramps)": gap(P, D),
        "pod to dock, insertion angle": gap(P_in, D),
        "cover to dock": gap(C, D),
    }
    if XIAO_STEP:
        X = xiao_from_step(XIAO_STEP)
        Xc = cq.Compound.makeCompound(X.vals())
        rep["xiao_step_check"] = {n: {"interference_mm3": round(h.val().intersect(Xc).Volume(), 4),
                                      "min_gap_mm": round(h.val().distance(Xc), 3)} for n, h in housing.items()}
    asm = (cq.Assembly(name="disctracker_housing_revC")
           .add(D, name="dock", color=cq.Color(0.16, 0.42, 0.85, 1))
           .add(P, name="pod", color=cq.Color(0.80, 0.81, 0.84, 1))
           .add(C, name="cover", color=cq.Color(0.55, 0.56, 0.60, 1))
           .add(M["pcb"], name="pcb", color=cq.Color(0.10, 0.33, 0.18, 1))
           .add(ref["xiao"], name="xiao", color=cq.Color(0.15, 0.15, 0.17, 1))
           .add(ref["parts"], name="parts", color=cq.Color(0.08, 0.08, 0.08, 1))
           .add(M["battery"], name="battery", color=cq.Color(0.75, 0.62, 0.25, 1)))
    asm.save(f"{OUT}/housing_assembly.step")
    json.dump(rep, open(f"{OUT}/report.json", "w"), indent=1)
    print(json.dumps(rep, indent=1))
