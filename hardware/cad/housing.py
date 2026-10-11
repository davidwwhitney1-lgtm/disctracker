#!/usr/bin/env python3
"""DiscTracker housing, rev B (CadQuery): click-in pod, glued dock, dock-gluing jig.

usage: python housing.py [out_dir] [--xiao-step PATH]

Writes STEP (for SolidWorks) and STL (for printing) per part, an assembly STEP, and report.json with
every fit, gap, stack-up, snap force and mass. --xiao-step additionally checks the parts against Seeed's
XIAO nRF52840 STEP model (not redistributed here).

Frame (same as the PCB): origin on the spin axis, +X toward the XIAO's USB-C flat, +Y up as seen from the
sensor face. +Z points toward the disc's flight plate; z = 0 is the plate underside, which the pod's lid
touches. All dimensions in mm.

How it fits together
  pod    lid + wall around the board; a ridge at the top for the dock's spring fingers; a flat with a
         USB-C port; two press-to-release latch arms at +/-90 deg. Board, XIAO and battery inside.
  cover  closes the bottom. Carries the reset-button flexure (force-limited plunger + hard stop), the
         LED window with a light shroud, and the buzzer's front chamber. 3 x M2 countersunk screws from
         the lid side pass through the board's alignment holes into the cover's columns and clamp the
         board between the lid bosses and the columns.
  dock   ring glued under the disc. Its flat keys the pod one way round, four spring fingers snap under
         the pod's ridge (click, zero-play preload, centering), and two window posts catch the pod's
         latches (positive lock). Squeeze both latches through the windows and pull to remove.
  jig    frame that self-centres on the disc rim + sliding plunger shaped like the pod's top; the dock
         clips onto the plunger, which places it on the plate centred and keyed.
"""
import json, math, os, sys
import cadquery as cq

HERE = os.path.dirname(os.path.abspath(__file__))
args = [a for a in sys.argv[1:]]
XIAO_STEP = None
if "--xiao-step" in args:
    i = args.index("--xiao-step"); XIAO_STEP = args[i + 1]; del args[i:i + 2]
OUT = args[0] if args else os.path.join(HERE, "out")
BOARD = json.load(open(os.path.join(HERE, "board_parts.json")))

# =============================================================== process and fit classes (JLC3DP MJF)
MATERIAL = "PA11-HP (MJF)"       # recommended: 50 % elongation, takes the flexures' strain. PA12-HP fits but see report
E_MOD = 1800.0                   # MPa, HP PA11/PA12 (XY and Z)
EPS_ALLOW = {"PA11-HP": 6.7, "PA12-HP": 2.7}   # %, 1/3 of Z elongation at yield (HP snap-fit handbook)
DENSITY = {"PA11-HP": 1.05, "PA12-HP": 1.01}   # g/cm3
MU = 0.3                         # nylon on nylon
TOL = 0.10                       # +/- per printed feature (radius or height) used in the stack-ups:
                                 # MJF holds ~+/-0.2 % (>=0.2 mm on diameters); JLC quotes +/-0.3 worst case
C_LOC = 0.30                     # radial clearance where a part only needs to locate (ridge, key, posts)
C_BOARD = 0.40                   # board edge to pod wall: board is located by the screws, never by the wall
C_MOVE = 0.60                    # slot width around flexures (JLC: >= 0.6 for moving parts)
REVEAL = 0.20                    # visible cover-to-wall gap

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
# ridge the dock fingers hold: lead-in from the lid edge, apex, 40 deg underside
R_RIDGE = R_OUT + 1.3                           # 30.7
RIDGE_R0 = R_OUT - 0.05                         # lead-in starts here on the lid edge
Z_APEX = (-1.45, -1.65)
BETA = 40.0                                     # underside angle from the axis (preload vs pull-off force)
Z_RIDGE_FOOT = Z_APEX[1] - (R_RIDGE - R_OUT) / math.tan(math.radians(BETA))
# M2 x 6 countersunk screws (nylon or brass - nothing magnetic near the magnetometer)
SCREW_CLR, CSK_D = 2.3, 4.1
BOSS_R = 2.3
LID_POSTS = [(11.0, 7.0), (-11.0, 7.0), (11.0, -7.0), (-11.0, -7.0)]   # rest on bare board, clear of parts
POST_GAP = 0.05
# USB-C: full-depth opening for the plug's overmold (Apple accessory guideline >= 12.45 x 6.60, full radius,
# plus 0.25 per side for print and XIAO position). The receptacle face sits 0.8 behind the outer flat.
USB_OPEN_W, USB_OPEN_H = 13.10, 7.20
BEZEL_T, BEZEL_C = 1.0, 0.30                    # cover posts beside the receptacle (close the side gaps)
# latch arms (press to release), circumferential cantilevers at +/-90 deg
R_ARM = (R_OUT + 0.9, R_OUT + 2.5)              # 0.9 gap to the wall = squeeze stop; 1.6 thick
Z_ARM = (-8.00, -5.00)
ARM_L = 10.0                                    # root to block, arc length at the arm's mid radius
BLOCK_W = 5.0
R_BLOCK = R_ARM[1] + 0.9                        # catch face 0.6 over the sill
Z_SHOULDER = -2.30                              # flat underside of the ridge above each latch block
SHOULDER_GAP = 0.60                             # block top to shoulder: overload backstop, wide enough not to fuse in MJF
Z_BLOCK = (-6.00, Z_SHOULDER - SHOULDER_GAP)    # catch face at the bottom, 35 deg lead-in on top
ROOT_W = 3.0
TEXT = "DISCTRACKER"

# =============================================================== cover
R_COV = R_IN - REVEAL
X_COV = X_FIN - REVEAL
CH_COV = 0.4
COL_R = 1.9
PILOT_D, PILOT_DEPTH = 1.6, 3.6                 # M2 x 6 thread-forming into nylon: 3 mm of thread, shallow enough to depowder
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

# =============================================================== dock
T_GLUE = 0.25                                   # VHB / 300LSE tape; the fingers absorb 0.1-0.4
Z_DTOP = -T_GLUE
R_D_IN = R_RIDGE + C_LOC                        # 31.0
R_D_OUT = 34.5
Z_FLANGE = (-1.50, Z_DTOP)
X_DKEY = X_FOUT + C_LOC                         # 28.2 flat key face
R_KEY, Z_KEY_BOT = 32.0, -2.05                  # key block stays above a 7.0 mm USB-C overmold
# spring fingers: circumferential cantilevers under the flange, bump at the tip
R_FING = (R_D_IN, R_D_IN + 1.13)
FING_H = 3.0                                    # axial height: stiff against the pod's push, radial stiffness from the 1.13 thickness
R_BUMP = R_RIDGE - 1.0                          # bump tip, free state (engagement 1.0)
DELTA0 = 0.50                                   # nominal finger deflection when seated (engagement 1.0)
Z_BUMP = Z_APEX[1] - (R_RIDGE - R_BUMP - DELTA0) / math.tan(math.radians(BETA))   # bump top edge
Z_FING = (Z_BUMP - FING_H, Z_BUMP)
FINGERS = [(35, 55), (-35, -55), (145, 125), (-145, -125)]   # (root, tip) deg, mirror-symmetric
BUMP_W = 3.0
# window posts for the latches
R_POST = (R_BLOCK - 0.6, R_BLOCK - 0.6 + 1.0)  # sill inner face 0.6 inside the block's catch, 0.3 past the arm
WIN_W = BLOCK_W + 2 * 0.3
BAR_W = 1.5
PLAY = 0.50                                     # latch catch to sill when the lid sits on the plate
Z_SILL = (Z_BOT + 0.02, Z_BLOCK[0] - PLAY)

# =============================================================== jig
DISC_OD = 211.0                                 # for the preview only; the cone fits 205-219 mm discs
RIM_DEPTH = 11.0                                # plate underside to rim bottom, preview only
SHAFT_R, JIG_CLR = 6.0, 0.25
CONE_R = (102.0, 110.0)
SPOKES = (90, 210, 330)


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


def wedge(P, beta):
    """axial force to push a face at beta (deg from the axis) past a spring of radial force P"""
    t = math.tan(math.radians(beta))
    return P * (MU + t) / (1 - MU * t)


# =============================================================== pod
def pod():
    prof = [(0, 0), (RIDGE_R0, 0), (R_RIDGE, Z_APEX[0]), (R_RIDGE, Z_APEX[1]), (R_OUT, Z_RIDGE_FOOT),
            (R_OUT, Z_BOT + CH_BOT), (R_OUT - CH_BOT, Z_BOT), (0, Z_BOT)]
    p = sector(prof)
    p = p.cut(box(X_FOUT, 40, -40, 40, Z_BOT - 1, 1))                          # USB-C flat
    yv = math.sqrt(R_OUT ** 2 - X_FOUT ** 2)
    try:
        p = p.edges(cq.selectors.BoxSelector((X_FOUT - 0.05, -yv - 0.05, Z_BOT), (X_FOUT + 0.05, yv + 0.05, Z_RIDGE_FOOT))).edges("|Z").fillet(0.8)
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
    # latch arms, with a flat-bottomed shoulder in the ridge above each hook (overload backstop)
    rm = (R_ARM[0] + R_ARM[1]) / 2
    a_sh = deg(BLOCK_W / 2 + 0.6, rm)
    for a in (90, -90):
        p = p.cut(sector([(R_OUT, Z_SHOULDER), (R_RIDGE + 1, Z_SHOULDER), (R_RIDGE + 1, Z_RIDGE_FOOT - 0.1), (R_OUT, Z_RIDGE_FOOT - 0.1)],
                         a - a_sh, a + a_sh))
        p = p.union(sector([(R_OUT - 0.1, Z_APEX[0]), (R_RIDGE, Z_APEX[0]), (R_RIDGE, Z_SHOULDER), (R_OUT - 0.1, Z_SHOULDER)],
                           a - a_sh, a + a_sh))
    p = p.union(latch()).union(latch().mirror("XZ"))
    # lid: name and a front mark (engraved 0.4)
    p = p.cut(cq.Workplane("XY").workplane(offset=-0.4).center(-1.5, -4.5)
              .text(TEXT, 4.6, 0.5, kind="bold", font="DejaVu Sans", halign="center", valign="center"))
    p = p.cut(prism([(18.5, -2.4), (18.5, 2.4), (22.5, 0)], -0.4, 0.1))
    return p


def latch():
    """+90 deg latch: arm from the root (toward +X) to the hook block at 90 deg"""
    rm = (R_ARM[0] + R_ARM[1]) / 2
    a_blk = deg(BLOCK_W / 2, rm)
    a_root = 90 - a_blk - deg(ARM_L, rm)
    arm = sector([(R_ARM[0], Z_ARM[0]), (R_ARM[1], Z_ARM[0]), (R_ARM[1], Z_ARM[1]), (R_ARM[0], Z_ARM[1])], a_root, 90 + a_blk)
    root = sector([(R_OUT - 0.3, Z_ARM[0]), (R_ARM[1], Z_ARM[0]), (R_ARM[1], Z_ARM[1]), (R_OUT - 0.3, Z_ARM[1])],
                  a_root - deg(ROOT_W, rm), a_root)
    # root fillet (R ~0.8) in the gap behind the arm
    t0 = math.radians(a_root)
    def xy(r, a):
        return (r * math.cos(a), r * math.sin(a))
    fil = prism([xy(R_OUT - 0.1, t0), xy(R_ARM[0] + 0.05, t0), xy(R_ARM[0] + 0.05, t0 + 0.8 / rm)], Z_ARM[0], Z_ARM[1])
    blk = sector([(R_ARM[0], Z_BLOCK[1]), (R_BLOCK - 0.7, Z_BLOCK[1]), (R_BLOCK, Z_BLOCK[1] - 1.0),
                  (R_BLOCK, Z_BLOCK[0]), (R_ARM[1], Z_BLOCK[0]), (R_ARM[1], Z_ARM[0]), (R_ARM[0], Z_ARM[0])],
                 90 - a_blk, 90 + a_blk)
    # two finger grooves across the block face
    g = None
    for zc in ((Z_BLOCK[0] + Z_BLOCK[1] - 1.0) / 2,):
        s = sector([(R_BLOCK - 0.25, zc - 0.22), (R_BLOCK + 0.1, zc - 0.22), (R_BLOCK + 0.1, zc + 0.22),
                    (R_BLOCK - 0.25, zc + 0.22)], 90 - a_blk - 1, 90 + a_blk + 1)
        g = s if g is None else g.union(s)
    return arm.union(root).union(fil).union(blk.cut(g))


# =============================================================== cover
def cover():
    c = sector([(0, Z_BOT), (R_COV - CH_COV, Z_BOT), (R_COV, Z_BOT + CH_COV), (R_COV, Z_CI), (0, Z_CI)])
    c = c.cut(box(X_COV, 40, -40, 40, Z_BOT - 1, 1))
    c = c.edges(cq.selectors.BoxSelector((X_COV - 0.05, -30, Z_BOT - 0.05), (X_COV + 0.05, 30, Z_BOT + 0.05))).chamfer(CH_COV)
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
    c = c.cut(cyl(22.6, -6.1, 1.4, Z_BOT - 0.1, Z_BOT + 0.3).cut(cyl(22.6, -6.1, 0.6, Z_BOT - 1, Z_BOT + 1)))
    return c


# =============================================================== dock
def dock():
    zf0, zf1 = Z_FLANGE
    d = sector([(R_D_IN, zf1), (R_D_OUT - 0.3, zf1), (R_D_OUT, zf1 - 0.3), (R_D_OUT, zf0 + 0.4),
                (R_D_OUT - 0.4, zf0), (R_D_IN + 0.3, zf0), (R_D_IN, zf0 + 0.3)])
    # flat key (one way in); bottom stays above a 7 mm USB-C overmold
    key = box(X_DKEY, R_KEY + 1, -20, 20, Z_KEY_BOT, zf1).intersect(cyl(0, 0, R_KEY, Z_KEY_BOT, zf1))
    key = key.cut(prism([(29.0, -1.6), (29.0, 1.6), (30.8, 0)], Z_KEY_BOT - 0.1, Z_KEY_BOT + 0.3))   # "front" mark
    d = d.union(key)
    # spring fingers
    rm = (R_FING[0] + R_FING[1]) / 2
    for a_root, a_tip in FINGERS:
        s = 1 if a_tip > a_root else -1
        lo, hi = sorted((a_root, a_tip))
        d = d.union(sector([(R_FING[0], Z_FING[0]), (R_FING[1], Z_FING[0]), (R_FING[1], Z_FING[1]), (R_FING[0], Z_FING[1])], lo, hi))
        r0, r1 = sorted((a_root, a_root - s * deg(3.0, rm)))      # solid root block across the flange (no twist)
        d = d.union(sector([(R_FING[0], Z_FING[0]), (R_D_OUT - 0.5, Z_FING[0]), (R_D_OUT - 0.5, zf0 + 0.01), (R_FING[0], zf0 + 0.01)], r0, r1))
        b0, b1 = sorted((a_tip, a_tip - s * deg(BUMP_W, R_D_IN)))
        zb = Z_BUMP
        zt = zb + 0.4 / math.tan(math.radians(BETA))
        bump = [(R_D_IN + 0.1, zt), (R_BUMP + 0.4, zt), (R_BUMP, zb), (R_BUMP, zb - 0.3),
                (R_D_IN, Z_FING[0] + 0.0), (R_D_IN + 0.1, Z_FING[0])]
        d = d.union(sector(bump, b0, b1))
    # window posts for the latches
    pm = (R_POST[0] + R_POST[1]) / 2
    for s in (1, -1):
        a = 90 * s
        hw, ww = deg(WIN_W / 2 + BAR_W, pm), deg(WIN_W / 2, pm)
        post = sector([(R_POST[0], Z_SILL[0]), (R_POST[1], Z_SILL[0]), (R_POST[1], zf0 + 0.01), (R_POST[0], zf0 + 0.01)], a - hw, a + hw)
        post = post.cut(sector([(R_POST[0] - 1, Z_SILL[1]), (R_POST[1] + 1, Z_SILL[1]), (R_POST[1] + 1, zf0 + 0.5),
                                (R_POST[0] - 1, zf0 + 0.5)], a - ww, a + ww))
        post = post.cut(sector([(R_POST[0] - 0.01, Z_SILL[0] - 0.01), (R_POST[0] + 0.4, Z_SILL[0] - 0.01),
                                (R_POST[0] - 0.01, Z_SILL[0] + 0.4)], a - hw - 1, a + hw + 1))   # lead-in under the sill
        d = d.union(post)
    return d


# =============================================================== jig
def jig_plunger():
    zr = Z_RIDGE_FOOT
    prof = [(0, 0), (RIDGE_R0, 0), (R_RIDGE, Z_APEX[0]), (R_RIDGE, Z_APEX[1]), (R_OUT, zr), (R_OUT, zr - 1.0),
            (R_OUT - 0.6, zr - 1.6), (SHAFT_R + 2.0, zr - 1.6), (SHAFT_R, zr - 3.6), (SHAFT_R, -62.0), (0, -62.0)]
    p = sector(prof).cut(box(X_FOUT, 40, -40, 40, -70, 1))
    # lighten the head from behind, keep three ribs
    pocket = sector([(SHAFT_R + 2.5, -1.6), (R_OUT - 1.4, -1.6), (R_OUT - 1.4, zr - 2.0), (SHAFT_R + 2.5, zr - 2.0)])
    for a in (90, 210, 330):
        pocket = pocket.cut(box(0, 40, -0.75, 0.75, -10, 0).rotate((0, 0, 0), (0, 0, 1), a))
    p = p.cut(pocket.cut(box(X_FOUT - 1.2, 40, -40, 40, -10, 1)))
    return p


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
    s["pod ridge to dock flange (radial)"] = rec(C_LOC, [TOL, TOL, 0.05], need_min=0.0)
    s["pod flat to dock key"] = rec(C_LOC, [TOL, TOL], need_min=0.0)
    s["finger deflection when seated"] = rec(DELTA0, [TOL, TOL, 0.10, TOL, 0.05], need_min=0.0, need_max=R_RIDGE - R_BUMP)
    s["latch catch to sill (play)"] = rec(PLAY, [TOL, TOL, 0.10, 0.05], need_min=0.0)
    s["latch block to window side"] = rec(0.3, [TOL, TOL], need_min=0.0)
    s["latch block to its overload shoulder (same part)"] = rec(SHOULDER_GAP, [0.05, 0.05], need_min=0.5)
    s["latch arm to sill inner face (radial)"] = rec(R_POST[0] - R_ARM[1], [TOL, TOL, 0.05], need_min=0.0)
    s["USB-C 12.35x6.5 overmold to opening (per side, Y)"] = rec((USB_OPEN_W - 12.35) / 2, [TOL, 0.10, 0.075, 0.10], need_min=0.0)
    s["USB-C 12.35x6.5 overmold to opening (per side, Z)"] = rec((USB_OPEN_H - 6.50) / 2, [TOL, 0.05, 0.10, 0.05], need_min=0.0)
    s["USB-C receptacle to bezel posts"] = rec(BEZEL_C, [TOL, 0.10, 0.075], need_min=0.0)
    s["reset plunger to switch at rest (>-0.15 = <1.6 N, not actuated)"] = rec(S_PRE, [TOL, 0.05, 0.05, 0.03, SW_H_TOL], need_min=-0.15)
    s["reset switch force at the stop, N"] = rec(cant(2 * SB_HW, SB_T, SW_C[0] - SB_X[1], 1)[0] * X_SB_NOM,
                                                 [cant(2 * SB_HW, SB_T, SW_C[0] - SB_X[1], 1)[0] * c for c in (SW_H_TOL, 0.07, 0.05)],
                                                 need_min=1.3 * SW_FORCE, need_max=6.5)
    s["LED shroud to LEDs"] = rec(SHROUD_GAP, [TOL, 0.05, 0.05], need_min=0.0)
    s["buzzer chamber rim to buzzer"] = rec(BUZ_GAP, [TOL, 0.10, 0.05], need_min=0.0)
    return s


def mechanics():
    out = {}
    rm = (R_FING[0] + R_FING[1]) / 2
    Lf = math.radians(abs(FINGERS[0][1] - FINGERS[0][0])) * rm - BUMP_W / 2
    tf = R_FING[1] - R_FING[0]
    eng = R_RIDGE - R_BUMP
    kf, _, _ = cant(FING_H, tf, Lf, 1)
    # on the way in, the ridge's apex rides up the bump's long lower face
    lead = math.degrees(math.atan((R_D_IN - R_BUMP) / ((Z_BUMP - 0.3) - Z_FING[0])))
    pre = [kf * d * (math.tan(math.radians(BETA)) - MU) / (1 + MU * math.tan(math.radians(BETA))) * 4
           for d in (DELTA0 - 0.30, DELTA0, DELTA0 + 0.30)]
    out["dock fingers"] = {"count": 4, "length": round(Lf, 2), "thickness": tf, "height": FING_H,
                           "stiffness_N_per_mm": round(kf, 2), "engagement": round(eng, 2),
                           "strain_at_full_deflection_pct": round(cant(FING_H, tf, Lf, eng + TOL)[2], 2),
                           "preload_total_N_min_nom_max": [round(x, 2) for x in pre],
                           "insert_lead_deg": round(lead, 1),
                           "insert_force_total_N": round(4 * wedge(kf * eng, lead), 1),
                           "pull_off_force_total_N": round(4 * wedge(kf * eng, BETA), 1),
                           "vertical_stiffness_N_per_mm": round(E_MOD * tf * FING_H ** 3 / (4 * Lf ** 3), 1),
                           "sag_at_pull_off_mm": round(wedge(kf * eng, BETA) / (E_MOD * tf * FING_H ** 3 / (4 * Lf ** 3)), 2),
                           "vertical_stress_at_pull_off_MPa": round(wedge(kf * eng, BETA) * Lf / (tf * FING_H ** 2 / 6), 0)}
    ra = (R_ARM[0] + R_ARM[1]) / 2
    ta = R_ARM[1] - R_ARM[0]
    ba = Z_ARM[1] - Z_ARM[0]
    eng_l = R_BLOCK - R_POST[0]
    kl, Pl, el = cant(ba, ta, ARM_L, eng_l + 0.05)
    span = WIN_W
    zmod = (R_POST[1] - R_POST[0]) * (Z_SILL[1] - Z_SILL[0]) ** 2 / 6
    kv = E_MOD * ta * ba ** 3 / (4 * ARM_L ** 3)              # arm bending up toward the shoulder
    out["pod latches"] = {"count": 2, "length": ARM_L, "thickness": ta, "height": ba, "stiffness_N_per_mm": round(kl, 2),
                          "overload_backstop": f"hook rises {SHOULDER_GAP} mm then bears on the ridge shoulder; arm carries {kv * SHOULDER_GAP:.1f} N each up to then, strain {150 * ba * SHOULDER_GAP / ARM_L ** 2:.1f} %",
                          "engagement": round(eng_l, 2), "squeeze_force_each_N": round(Pl, 1),
                          "strain_at_squeeze_stop_pct": round(cant(ba, ta, ARM_L, R_ARM[0] - R_OUT)[2], 2),
                          "insert_force_total_N": round(2 * wedge(Pl, 35), 1),
                          "pull_out_capacity_total_N (sill yield, 48 MPa)": round(2 * 48 * zmod * 8 / span, 0),
                          "shoulder_bearing_capacity_total_N (60 MPa)": round(2 * 60 * BLOCK_W * (R_RIDGE - R_ARM[0]), 0),
                          "catch": "90 deg (positive): cannot be pulled out without squeezing"}
    Lsb = SB_X[2] - SB_X[1] - (SB_X[2] - SW_C[0])
    ksb = cant(2 * SB_HW, SB_T, Lsb, 1)[0]
    xr = [X_SB_NOM - 0.15, X_SB_NOM, X_SB_NOM + 0.15]
    kt = cant(TONGUE_Y[1] - TONGUE_Y[0], COVER_T, SW_C[0] - TONGUE_X[0], 1)[0]
    out["reset flexure"] = {"tongue_stiffness_N_per_mm": round(kt, 2), "springboard_stiffness_N_per_mm": round(ksb, 2),
                            "switch_force_at_stop_N_min_nom_max": [round(ksb * x, 2) for x in xr],
                            "switch_rated_N": SW_FORCE, "finger_force_at_stop_N": round(kt * G_PLUNGER + ksb * X_SB_NOM, 1),
                            "travel_to_stop_mm": round(G_PLUNGER, 2), "stop_strip_thickness": round(Z_USB_BOT - G_STOP - Z_BOT, 2),
                            "springboard_strain_pct_max": round(cant(2 * SB_HW, SB_T, Lsb, xr[2])[2], 2),
                            "tongue_strain_pct": round(cant(TONGUE_Y[1] - TONGUE_Y[0], COVER_T, SW_C[0] - TONGUE_X[0], G_PLUNGER)[2], 2),
                            "stop": "tongue strip lands on the USB-C shell; plunger and stop both reference the XIAO"}
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
    JF, JP = jig_frame(), jig_plunger()
    M = board_models()
    for name, part in (("pod", P), ("cover", C), ("dock", D), ("jig_frame", JF), ("jig_plunger", JP)):
        sol = part.solids().vals()
        assert len(sol) == 1 and part.val().isValid(), f"{name}: {len(sol)} solids, valid={part.val().isValid()}"
    rep = {"rev": "B", "material": MATERIAL,
           "depth_below_plate_mm": round(-Z_BOT, 2),
           "pod_mm": {"diameter_over_ridge": 2 * R_RIDGE, "wall_od": 2 * R_OUT, "over_latches": 2 * R_BLOCK,
                      "flat_to_centre": X_FOUT},
           "dock_mm": {"od": 2 * R_D_OUT, "lowest_point": round(Z_SILL[0], 2)},
           "z_stack_mm": {"lid_top": 0, "lid_underside": -LID_T, "board_top": round(Z_BT, 3), "board_bottom": round(Z_BB, 3),
                          "xiao_face": round(Z_XT, 3), "usb_c_centre": round(Z_USB, 3), "cover_inner": round(Z_CI, 3),
                          "pod_bottom": round(Z_BOT, 3)},
           "mass_g": {}, "stackups": stackups(), "mechanics": mechanics(),
           "stackups_at_tol_0.2 (robustness)": {k: {"rss": v["rss"], "ok_rss": v["ok_rss"]} for k, v in stackups(0.2).items()}}
    mech = rep["mechanics"]
    worst = max(mech["dock fingers"]["strain_at_full_deflection_pct"], mech["pod latches"]["strain_at_squeeze_stop_pct"],
                mech["reset flexure"]["springboard_strain_pct_max"])
    rep["strain_check_pct"] = {"worst_flexure": worst, **{m: {"allowable": a, "ok": worst <= a} for m, a in EPS_ALLOW.items()}}
    rep["balance"] = {"note": "off-centre mass of each part (PA11); trim with solder on TP1-TP4 (r = 22 mm) after weighing"}
    for name, part in (("pod", P), ("cover", C), ("dock", D), ("jig_frame", JF), ("jig_plunger", JP)):
        vol = part.val().Volume() / 1000.0
        rep["mass_g"][name] = {k: round(vol * d, 2) for k, d in DENSITY.items()}
        if name in ("pod", "cover", "dock"):
            cg = part.val().Center()
            m = vol * DENSITY["PA11-HP"]
            rep["balance"][name] = {"cg_xy_mm": [round(cg.x, 3), round(cg.y, 3)], "g_mm": [round(m * cg.x, 2), round(m * cg.y, 2)]}
        cq.exporters.export(part, f"{OUT}/{name}.step")
        cq.exporters.export(part, f"{OUT}/{name}.stl", tolerance=0.01, angularTolerance=0.1)
    # reference models for the viewer
    ref = {"board": M["pcb"]}
    parts_top = [M[k] for k in M if k not in ("pcb", "battery") and not k.startswith(("XIAO", "USB", "shield", "reset", "LED", "mic", "IC"))]
    xiao = [M[k] for k in ("XIAO pcb", "USB-C", "shield", "reset", "LED rgb", "LED chg", "mic", "IC")]
    def fuse(lst):
        out = lst[0]
        for s in lst[1:]:
            out = out.union(s)
        return out
    ref["parts"] = fuse(parts_top)
    ref["xiao"] = fuse(xiao)
    ref["battery"] = M["battery"]
    ref["disc"] = disc_model()
    for k, v in ref.items():
        cq.exporters.export(v, f"{OUT}/ref_{k}.stl", tolerance=0.02, angularTolerance=0.15)
    # checks
    housing = {"pod": P, "cover": C, "dock": D}
    inter = report_shapes(housing, M)
    bumps = None
    for a_root, a_tip in FINGERS:
        lo, hi = sorted((a_tip, a_tip - (1 if a_tip > a_root else -1) * deg(BUMP_W + 0.2, R_D_IN)))
        sec = sector([(R_BUMP - 0.2, Z_FING[0] - 0.1), (R_D_IN + 0.2, Z_FING[0] - 0.1), (R_D_IN + 0.2, Z_FLANGE[0]),
                      (R_BUMP - 0.2, Z_FLANGE[0])], lo, hi)
        bumps = sec if bumps is None else bumps.union(sec)
    rep["designed_preload_overlap_mm3 (finger bumps on the ridge)"] = round(P.intersect(D).val().Volume(), 3)
    for a, b in (("pod", "cover"), ("pod", "dock (bumps excluded)"), ("cover", "dock")):
        if b.startswith("dock (b"):
            try:
                v = P.intersect(D.cut(bumps)).val().Volume()
            except Exception:
                v = 0.0
            if v > 1e-3:
                inter[f"{a} x {b}"] = round(v, 4)
            continue
        try:
            v = housing[a].intersect(housing[b]).val().Volume()
        except Exception:
            v = 0.0
        if v > 1e-3:
            inter[f"{a} x {b}"] = round(v, 4)
    jp = JP.intersect(D.cut(bumps))
    try:
        v = jp.val().Volume()
    except Exception:
        v = 0.0
    if v > 1e-3:
        inter["jig_plunger x dock"] = round(v, 4)
    rep["interference_mm3"] = inter
    rep["min_gap_mm"] = {
        "lid to U1 (centre IMU)": gap(P, M["U1"]),
        "lid to U2": gap(P, M["U2"]),
        "pod wall to board edge": gap(P.intersect(box(-40, 40, -40, 40, Z_BB - 0.3, Z_BT - 0.01)), M["pcb"]),
        "cover to USB-C shell": gap(C, M["USB-C"]),
        "cover to battery": gap(C, M["battery"]),
        "cover to shield": gap(C, M["shield"]),
        "plunger to reset switch": gap(C, M["reset"]),
        "stop strip to USB-C shell (designed)": round(G_STOP, 3),
        "LED shroud to LEDs": min(gap(C, M["LED rgb"]), gap(C, M["LED chg"])),
        "buzzer chamber to buzzer": gap(C, M["BZ1"]),
        "pod to dock (bumps excluded)": gap(P, D.cut(bumps)),
        "cover to dock": gap(C, D),
    }
    if XIAO_STEP:
        X = xiao_from_step(XIAO_STEP)
        Xc = cq.Compound.makeCompound(X.vals())
        rep["xiao_step_check"] = {n: {"interference_mm3": round(h.val().intersect(Xc).Volume(), 4),
                                      "min_gap_mm": round(h.val().distance(Xc), 3)} for n, h in housing.items()}
    asm = (cq.Assembly(name="disctracker_housing_revB")
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
