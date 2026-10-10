#!/usr/bin/env python3
"""DiscTracker housing: click-in pod + glued dock + floor cover + dock-gluing jig (CadQuery).

usage: python housing.py <out_dir>
Writes STEP (for SolidWorks) and STL (for printing) per part, an assembly STEP, and mass estimates.

Frame (same as the PCB): origin on the spin axis, +X toward the USB-C flat, +Y up as seen from the
sensor face. +Z points toward the disc's flight plate. z = 0 is the flight plate underside, where
the dock's glued face and the pod's top both sit.
All dimensions in mm. Change the parameters below and re-run.
"""
import math, sys, json
import cadquery as cq

OUT = sys.argv[1] if len(sys.argv) > 1 else "."

# ---------------------------------------------------------------- PCB (from hardware/kicad)
BOARD_R = 28.0          # 56 mm round board
BOARD_FLAT_X = 26.5     # flat for the USB-C plug
BOARD_T = 0.8
HOLE_R, HOLE_ANG, HOLE_D = 25.6, (30, 150, 250), 2.1
TOP_PARTS_H = 0.83      # tallest sensor-face part (LSM6DSV320X)
BOTTOM_PARTS_H = 4.0    # XIAO incl. USB-C (measured); battery 3.8, buzzer 1.9
XIAO_C, XIAO_L, XIAO_W = (15.0, 0.0), 21.0, 17.8
BAT_C, BAT_X, BAT_Y, BAT_T = (-6.54, 0.0), 19.75, 26.02, 3.8
BUZ_C, BUZ_S, BUZ_T = (0.0, 21.5), 9.0, 1.9

# ---------------------------------------------------------------- pod
WALL = 0.9              # side wall
LID = 0.8               # top (sensor face side), against the flight plate
COVER = 0.6             # snap-in floor cover
GAP_R = 0.3             # board edge to wall
CLR_TOP = 0.17          # sensor parts to lid
CLR_BOT = 0.3           # XIAO to cover
R_IN = BOARD_R + GAP_R                  # 28.3
R_OUT = R_IN + WALL                     # 29.2
Z_BOARD_TOP = -(LID + TOP_PARTS_H + CLR_TOP)          # -1.80
Z_BOARD_BOT = Z_BOARD_TOP - BOARD_T                   # -2.60
Z_COVER_TOP = Z_BOARD_BOT - BOTTOM_PARTS_H - CLR_BOT  # -6.90
Z_POD_BOT = Z_COVER_TOP - COVER                       # -7.50
POD_H = -Z_POD_BOT
BOSS_D, PIN_D, PIN_STAKE = 3.6, 1.9, 0.6

# click-in ridge on the pod wall, near the bottom
RIDGE = 0.6                             # radial height of the ridge
Z_RIDGE_TOP, Z_RIDGE_BOT = -5.3, -6.3   # top ramp starts at Z_RIDGE_TOP, flat-ish catch at the bottom

# USB-C opening in the wall at +X (plug overmold ~12 x 6.5 mm)
USB_W = 12.8
Z_USB_TOP = Z_BOARD_BOT + 0.8

# key: tab on the pod at +X, notch in the dock
KEY_W, KEY_H, KEY_OUT = 3.0, 1.5, 0.9

# ---------------------------------------------------------------- dock (glued to the disc)
DOCK_RI = R_OUT + 0.25                  # 29.45: centers the pod to +/-0.25 mm
DOCK_RO = 33.0
DOCK_T = 1.2
ARM_ANG = (90, 210, 330)                # three snap arms (clear of the USB opening at 0 deg)
ARM_W = 9.0                             # arc width
ARM_T = 0.9                             # radial thickness (flex)
ARM_RI = R_OUT + RIDGE + 0.1            # arm inner face clears the ridge
HOOK_IN = R_OUT + 0.15                  # hook reaches in to here (engagement = R_OUT+RIDGE-HOOK_IN)

# ---------------------------------------------------------------- jig (glue the dock centered)
DISC_OD = 211.0         # measure your discs (PDGA range ~210-213 for drivers)
RIM_TO_PLATE = 11.0     # rim bottom edge to plate underside near r = 31 mm - MEASURE per disc mould


def revolve_profile(pts, a0=0, a1=360):
    """revolve an (r, z) polygon about Z between angles a0..a1 (deg)"""
    wp = cq.Workplane("XZ").polyline(pts).close()
    solid = wp.revolve(a1 - a0, (0, 0, 0), (0, 1, 0))
    return solid.rotate((0, 0, 0), (0, 0, 1), a0)


def board_outline(r, flat_x, z0, h):
    disk = cq.Workplane("XY").workplane(offset=z0).circle(r).extrude(h)
    cut = cq.Workplane("XY").workplane(offset=z0 - 1).center(flat_x + 50, 0).rect(100, 100).extrude(h + 2)
    return disk.cut(cut)


def pod():
    body = cq.Workplane("XY").workplane(offset=Z_POD_BOT).circle(R_OUT).extrude(POD_H)
    cavity = cq.Workplane("XY").workplane(offset=Z_POD_BOT - 1).circle(R_IN).extrude(-LID - Z_POD_BOT + 1)
    body = body.cut(cavity)
    # ridge for the click-in hooks (40 deg insertion ramp on top, 10 deg catch underneath)
    ridge = revolve_profile([(R_OUT - 0.01, Z_RIDGE_TOP), (R_OUT + RIDGE, Z_RIDGE_TOP - 0.5),
                             (R_OUT + RIDGE, Z_RIDGE_BOT + 0.1), (R_OUT - 0.01, Z_RIDGE_BOT)])
    body = body.union(ridge)
    # standoffs + locating pins through the PCB holes
    for a in HOLE_ANG:
        x, y = HOLE_R * math.cos(math.radians(a)), HOLE_R * math.sin(math.radians(a))
        boss = cq.Workplane("XY").workplane(offset=Z_BOARD_TOP).center(x, y).circle(BOSS_D / 2).extrude(-LID - Z_BOARD_TOP + 0.01)
        pin = cq.Workplane("XY").workplane(offset=Z_BOARD_BOT - PIN_STAKE).center(x, y).circle(PIN_D / 2).extrude(PIN_STAKE + BOARD_T + 0.01)
        body = body.union(boss).union(pin)
    # USB-C opening through wall + ridge
    usb = cq.Workplane("XY").workplane(offset=Z_POD_BOT - 1).center(R_IN + 2.5, 0).rect(6, USB_W).extrude(Z_USB_TOP - Z_POD_BOT + 1)
    body = body.cut(usb)
    # key tab on top of the wall at +X (above the USB opening)
    key = cq.Workplane("XY").workplane(offset=-KEY_H).center(R_OUT + KEY_OUT / 2 - 0.2, 0).rect(KEY_OUT + 0.4, KEY_W).extrude(KEY_H)
    body = body.union(key)
    # "front" arrow pointer engraved in the lid (shallow), visible from the cavity side is not needed:
    arrow = (cq.Workplane("XY").workplane(offset=-0.25).polyline([(20, -2), (24, 0), (20, 2)]).close().extrude(0.25))
    body = body.cut(arrow)
    return body


def cover():
    c = cq.Workplane("XY").workplane(offset=Z_POD_BOT).circle(R_IN - 0.1).extrude(COVER)
    # USB-C opening
    c = c.cut(cq.Workplane("XY").workplane(offset=Z_POD_BOT - 1).center(R_IN, 0).rect(2 * (R_IN - 25.8), USB_W).extrude(3))
    # sound hole under the buzzer, window under the XIAO's LEDs (next to its USB-C; verify on your XIAO)
    c = c.cut(cq.Workplane("XY").workplane(offset=Z_POD_BOT - 1).center(*BUZ_C).circle(1.5).extrude(3))
    c = c.cut(cq.Workplane("XY").workplane(offset=Z_POD_BOT - 1).center(20.5, 0).rect(5.0, 7.0).extrude(3))
    # three snap bumps that click into the pod wall's dimples
    for a in (60, 180, 300):
        x, y = (R_IN - 0.1) * math.cos(math.radians(a)), (R_IN - 0.1) * math.sin(math.radians(a))
        bump = cq.Workplane("XY").sphere(0.3).translate((x, y, Z_POD_BOT + COVER / 2))
        c = c.union(bump)
    # pull tab notch for a fingernail at 180 deg
    c = c.cut(cq.Workplane("XY").workplane(offset=Z_POD_BOT - 1).center(-(R_IN - 0.8), 0).rect(1.6, 4.0).extrude(1.3))
    return c


def pod_with_dimples(p):
    for a in (60, 180, 300):
        x, y = (R_IN - 0.1) * math.cos(math.radians(a)), (R_IN - 0.1) * math.sin(math.radians(a))
        p = p.cut(cq.Workplane("XY").sphere(0.35).translate((x, y, Z_POD_BOT + COVER / 2)))
    return p


def dock():
    ring = revolve_profile([(DOCK_RI, 0), (DOCK_RO, 0), (DOCK_RO, -DOCK_T), (DOCK_RI, -DOCK_T)])
    # key notch at +X
    ring = ring.cut(cq.Workplane("XY").workplane(offset=-DOCK_T - 1).center(DOCK_RI + KEY_OUT / 2, 0)
                    .rect(KEY_OUT + 0.6, KEY_W + 0.4).extrude(DOCK_T + 2))
    half = math.degrees(ARM_W / 2 / (ARM_RI + ARM_T))
    z_hook_top = Z_RIDGE_BOT - 0.05
    for a in ARM_ANG:
        # arm: flexes outward, hook catches under the pod ridge, outward lip for a fingernail
        prof = [(ARM_RI, -DOCK_T + 0.01), (ARM_RI + ARM_T, -DOCK_T + 0.01),
                (ARM_RI + ARM_T, Z_POD_BOT + 0.6), (ARM_RI + ARM_T + 0.6, Z_POD_BOT + 0.3),
                (ARM_RI + ARM_T + 0.6, Z_POD_BOT), (HOOK_IN + 0.6, Z_POD_BOT),
                (HOOK_IN, z_hook_top - 0.25), (HOOK_IN, z_hook_top), (ARM_RI, z_hook_top + 0.1)]
        ring = ring.union(revolve_profile(prof, a - half, a + half))
    # outer-edge notch at +X: keys the dock in the gluing jig (and marks "front")
    ring = ring.cut(cq.Workplane("XY").workplane(offset=-DOCK_T - 1).center(DOCK_RO, 0).rect(1.4, 2.4).extrude(DOCK_T + 2))
    return ring


def jig():
    """Sits on the upturned disc's rim (disc upside down) and holds the dock centered on the plate."""
    ring_ri = DISC_OD / 2 - 6
    skirt_ri = DISC_OD / 2 + 0.25
    top = 2.5
    j = revolve_profile([(ring_ri, 0), (skirt_ri + 2.0, 0), (skirt_ri + 2.0, -top - 4), (skirt_ri, -top - 4),
                         (skirt_ri, -top), (ring_ri, -top)])
    # tube that reaches down to the plate and presses the dock's outer band
    tube_ri, tube_ro = DOCK_RO - 1.0, DOCK_RO + 2.5
    tube = revolve_profile([(tube_ri, -top), (tube_ro, -top), (tube_ro, -top - RIM_TO_PLATE + DOCK_T),
                            (DOCK_RO + 0.2, -top - RIM_TO_PLATE + DOCK_T), (DOCK_RO + 0.2, -top - RIM_TO_PLATE),
                            (tube_ri, -top - RIM_TO_PLATE)]).translate((0, 0, 0))
    # the tube's inner step holds the dock (dock OD sits inside DOCK_RO + 0.2 for the last DOCK_T mm)
    j = j.union(tube)
    # nub in the tube's step that fits the dock's outer notch, so the dock goes in "front" (+X) first
    j = j.union(cq.Workplane("XY").workplane(offset=-top - RIM_TO_PLATE).center(DOCK_RO - 0.1, 0).rect(1.0, 2.0).extrude(DOCK_T))
    for a in (90, 210, 330):
        spoke = (cq.Workplane("XY").workplane(offset=-top).center((tube_ro + ring_ri) / 2, 0)
                 .rect(ring_ri - tube_ro + 1, 6).extrude(top).rotate((0, 0, 0), (0, 0, 1), a))
        j = j.union(spoke)
    # alignment pointer at +X ("front" = USB-C side) to line up with the disc's stamp
    j = j.union(cq.Workplane("XY").workplane(offset=-top).center(tube_ro + 6, 0).rect(12, 4).extrude(top))
    return j.mirror("XY")   # print flat; in use the jig is upside down over the upturned disc


def board_dummy():
    """Simplified PCB + parts for fit checks (not for manufacturing)."""
    b = board_outline(BOARD_R, BOARD_FLAT_X, Z_BOARD_BOT, BOARD_T)
    for a in HOLE_ANG:
        b = b.cut(cq.Workplane("XY").workplane(offset=Z_BOARD_BOT - 1).center(HOLE_R * math.cos(math.radians(a)),
                  HOLE_R * math.sin(math.radians(a))).circle(HOLE_D / 2).extrude(3))
    parts = []
    for x, y in ((0, 0), (20, 0), (-20, 0)):
        parts.append(cq.Workplane("XY").workplane(offset=Z_BOARD_TOP).center(x, y).rect(3.0, 2.5).extrude(TOP_PARTS_H))
    parts.append(cq.Workplane("XY").workplane(offset=Z_BOARD_BOT).center(*XIAO_C).rect(XIAO_L, XIAO_W).extrude(-1.2))
    parts.append(cq.Workplane("XY").workplane(offset=Z_BOARD_BOT - 1.0).center(XIAO_C[0] + XIAO_L / 2 - 3.2, 0).rect(7.6, 9.0).extrude(-3.0))
    parts.append(cq.Workplane("XY").workplane(offset=Z_BOARD_BOT).center(*BAT_C).rect(BAT_X, BAT_Y).extrude(-BAT_T))
    parts.append(cq.Workplane("XY").workplane(offset=Z_BOARD_BOT).center(*BUZ_C).rect(BUZ_S, BUZ_S).extrude(-BUZ_T))
    return b, parts


if __name__ == "__main__":
    import os
    os.makedirs(OUT, exist_ok=True)
    P = pod_with_dimples(pod())
    C = cover()
    D = dock()
    J = jig()
    board, parts = board_dummy()
    dens = {"PA12 (MJF/SLS)": 1.01, "PETG (FDM, 100%)": 1.27}
    report = {"pod_height_below_plate_mm": round(POD_H, 2),
              "pod_od_mm": round(2 * (R_OUT + RIDGE), 2), "dock_od_mm": 2 * DOCK_RO,
              "snap_engagement_mm": round(R_OUT + RIDGE - HOOK_IN, 2),
              "arm_flex_length_mm": round(-DOCK_T - (Z_RIDGE_BOT - 0.05), 2),
              "arm_strain_pct": round(100 * 1.5 * ARM_T * (R_OUT + RIDGE - HOOK_IN) / (-DOCK_T - Z_RIDGE_BOT) ** 2, 2),
              "mass_g": {}}
    for name, part in (("pod", P), ("cover", C), ("dock", D), ("jig", J)):
        vol = part.val().Volume() / 1000.0
        report["mass_g"][name] = {k: round(vol * d, 2) for k, d in dens.items()}
        cq.exporters.export(part, f"{OUT}/{name}.step")
        cq.exporters.export(part, f"{OUT}/{name}.stl", tolerance=0.02, angularTolerance=0.1)
    asm = (cq.Assembly(name="disctracker_housing")
           .add(D, name="dock", color=cq.Color(0.20, 0.45, 0.85, 1))
           .add(P, name="pod", color=cq.Color(0.85, 0.85, 0.88, 1))
           .add(C, name="cover", color=cq.Color(0.70, 0.70, 0.74, 1))
           .add(board, name="pcb", color=cq.Color(0.15, 0.35, 0.20, 1)))
    for i, p in enumerate(parts):
        asm.add(p, name=f"part{i}", color=cq.Color(0.1, 0.1, 0.1, 1))
    asm.save(f"{OUT}/housing_assembly.step")
    cq.exporters.export(board, f"{OUT}/pcb_dummy.stl", tolerance=0.02)
    pcomp = parts[0]
    for p in parts[1:]:
        pcomp = pcomp.union(p)
    cq.exporters.export(pcomp, f"{OUT}/pcb_parts_dummy.stl", tolerance=0.02)
    # interference check: pod/cover vs board + parts
    clash = {}
    names = ["pcb", "U1", "U2", "U3", "XIAO", "USB-C", "battery", "buzzer"]
    for nm, part in (("pod", P), ("cover", C), ("dock", D)):
        for i, q in enumerate([board] + parts):
            try:
                v = part.intersect(q).val().Volume()
            except Exception:
                v = 0
            if v > 1e-3:
                clash[f"{nm} x {names[i]}"] = round(v, 3)
    for a, b_ in (("pod", "dock"), ("pod", "cover"), ("cover", "dock")):
        A, Bp = {"pod": P, "dock": D, "cover": C}[a], {"pod": P, "dock": D, "cover": C}[b_]
        try:
            v = A.intersect(Bp).val().Volume()
        except Exception:
            v = 0
        if v > 1e-3:
            clash[f"{a} x {b_}"] = round(v, 3)
    report["interference_mm3"] = clash
    json.dump(report, open(f"{OUT}/report.json", "w"), indent=1)
    print(json.dumps(report, indent=1))
