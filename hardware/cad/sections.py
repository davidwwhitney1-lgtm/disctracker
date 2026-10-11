#!/usr/bin/env python3
"""Cross-section drawings of the rev B housing (true scale, filled sections).

usage: python sections.py [out_png]
Builds the parts from housing.py and slices them through the features that need checking:
the stack at the USB-C port, a latch, a dock finger, the reset mechanism, and the cover seen from below.
"""
import math, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import cadquery as cq
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.path import Path
from matplotlib.patches import PathPatch
import housing as H

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "renders", "sections.png")

COL = {"pod": "#c9cdd3", "cover": "#8f96a0", "dock": "#3d6fc4", "pcb": "#2e6b45", "xiao": "#3a3f46",
       "parts": "#22262b", "battery": "#c9a24a", "disc": "#d9a877"}
EDGE = "#1b2320"


def slice2d(shape, origin, normal, xdir):
    """filled section of a solid by a plane -> list of (outer, holes) polygons in plane coords"""
    pln = cq.Plane(origin=origin, xDir=xdir, normal=normal)
    big = cq.Solid.makeBox(600, 600, 300, cq.Vector(-300, -300, -300)).transformShape(pln.rG)
    out = []
    try:
        half = shape.val().intersect(big) if hasattr(shape, "val") else shape.intersect(big)
    except Exception:
        return out
    n = cq.Vector(*normal).normalized()
    for f in half.Faces():
        try:
            fn = f.normalAt()
        except Exception:
            continue
        if fn.dot(n) < 0.999 or abs(pln.toLocalCoords(f.Center()).z) > 1e-4:
            continue
        polys = []
        for w in [f.outerWire()] + f.innerWires():
            L = w.Length()
            N = max(60, int(L / 0.02))
            pts = [pln.toLocalCoords(w.positionAt(t)) for t in np.linspace(0, 1, N)]
            polys.append(np.array([(p.x, p.y) for p in pts]))
        out.append(polys)
    return out


def draw(ax, polys, color, alpha=1.0, hatch=None, lw=0.5):
    for rings in polys:
        verts, codes = [], []
        for r in rings:
            verts += list(r) + [r[0]]
            codes += [Path.MOVETO] + [Path.LINETO] * (len(r) - 1) + [Path.CLOSEPOLY]
        ax.add_patch(PathPatch(Path(verts, codes), facecolor=color, edgecolor=EDGE, lw=lw, alpha=alpha, hatch=hatch))


def note(ax, xy, text, dxy=(2, 2), size=6.5):
    ax.annotate(text, xy=xy, xytext=(xy[0] + dxy[0], xy[1] + dxy[1]), fontsize=size,
                arrowprops=dict(arrowstyle="-", lw=0.4, color=EDGE), color=EDGE)


def gapmark(ax, p0, p1, text, off=(0.3, 0), size=6):
    ax.annotate("", xy=p0, xytext=p1, arrowprops=dict(arrowstyle="<->", lw=0.5, color="#b23a2e", shrinkA=0, shrinkB=0))
    ax.text((p0[0] + p1[0]) / 2 + off[0], (p0[1] + p1[1]) / 2 + off[1], text, fontsize=size, color="#b23a2e", va="center")


def panel(ax, title, cut, xlim, ylim, items, extra=None):
    origin, normal, xdir = cut
    for name, shape, col, alpha in items:
        draw(ax, slice2d(shape, origin, normal, xdir), col, alpha)
    ax.set_xlim(*xlim); ax.set_ylim(*ylim); ax.set_aspect("equal")
    ax.set_title(title, fontsize=8, loc="left")
    ax.tick_params(labelsize=6)
    ax.grid(lw=0.2, color="#cbd4d0")
    if extra:
        extra(ax)


if __name__ == "__main__":
    P, C, D = H.pod(), H.cover(), H.dock()
    M = H.board_models()
    xiao = [M[k] for k in ("XIAO pcb", "USB-C", "shield", "reset", "LED rgb", "LED chg", "mic", "IC")]
    xiao_u = xiao[0]
    for s in xiao[1:]:
        xiao_u = xiao_u.union(s)
    others = [v for k, v in M.items() if k not in ("pcb", "battery") and not k.startswith(("XIAO", "USB", "shield", "reset", "LED", "mic", "IC"))]
    parts_u = others[0]
    for s in others[1:]:
        parts_u = parts_u.union(s)
    disc = H.disc_model()
    base = [("disc", disc, COL["disc"], 0.35), ("pcb", M["pcb"], COL["pcb"], 1), ("parts", parts_u, COL["parts"], 1),
            ("xiao", xiao_u, COL["xiao"], 1), ("battery", M["battery"], COL["battery"], 1),
            ("pod", P, COL["pod"], 1), ("cover", C, COL["cover"], 1), ("dock", D, COL["dock"], 1)]

    fig = plt.figure(figsize=(11.7, 12.2), dpi=170)
    gs = fig.add_gridspec(4, 2, height_ratios=[0.4, 1, 0.78, 1.15], hspace=0.3, wspace=0.12)

    # A: full section through the USB-C port (y = 0), looking from -Y
    ax = fig.add_subplot(gs[0, :])
    def a_extra(ax):
        for z, t in ((0, "plate / lid top  0"), (H.Z_BT, f"board top  {H.Z_BT:.2f}"), (H.Z_BB, f"board bottom  {H.Z_BB:.2f}"),
                     (H.Z_XT, f"XIAO face  {H.Z_XT:.2f}"), (H.Z_CI, f"cover inner  {H.Z_CI:.2f}"), (H.Z_BOT, f"pod bottom  {H.Z_BOT:.2f}")):
            ax.axhline(z, lw=0.3, ls=":", color="#5c6a65")
            ax.text(37.6, z, t, fontsize=5.5, color="#5c6a65", va="center", clip_on=False)
        note(ax, (27.0, H.Z_USB), "USB-C receptacle face X 27.0, opening 13.1 x 7.2 for the overmold", (-26.0, -3.9))
    panel(ax, "A  Section y = 0: stack-up and USB-C port (mm)", ((0, 0, 0), (0, -1, 0), (1, 0, 0)), (-37, 37), (-10.5, 4.5), base, a_extra)

    # B: latch (x = 0 plane, +Y side)
    ax = fig.add_subplot(gs[1, 0])
    def b_extra(ax):
        gapmark(ax, (H.R_BLOCK - 0.3, H.Z_SILL[1]), (H.R_BLOCK - 0.3, H.Z_BLOCK[0]), f" play {H.PLAY:.2f}", (0.15, 0))
        gapmark(ax, (H.R_OUT, -7.6), (H.R_ARM[0], -7.6), f"squeeze\nstop {H.R_ARM[0] - H.R_OUT:.1f}", (-0.6, -0.9))
        note(ax, (H.R_BLOCK, -5.5), "latch hook\n(square catch)", (1.2, 1.5))
        note(ax, (H.R_POST[1], -8.0), "dock sill", (1.0, -1.3))
    panel(ax, "B  Section x = 0: latch at +90 deg in the dock window", ((0, 0, 0), (1, 0, 0), (0, 1, 0)), (25.5, 36.5), (-10.0, 1.5), base, b_extra)

    # C: dock finger at its bump (radial plane through 54 deg)
    ax = fig.add_subplot(gs[1, 1])
    a = math.radians(54 - 1.5 * 180 / math.pi / H.R_D_IN)    # through the middle of the bump
    u = (math.cos(a), math.sin(a), 0)
    nrm = (math.sin(a), -math.cos(a), 0)
    def c_extra(ax):
        note(ax, (H.R_RIDGE, H.Z_APEX[1]), f"pod ridge, {H.BETA:.0f} deg underside", (1.5, 1.6))
        note(ax, (H.R_BUMP + H.DELTA0, H.Z_BUMP), f"finger bump (free shape drawn:\n{H.DELTA0:.2f} overlap = preload)", (2.2, -2.8))
        note(ax, (32.5, H.Z_FLANGE[1]), f"glue face (tape {H.T_GLUE})", (0.8, 1.2))
    panel(ax, "C  Radial section through a dock finger (54 deg)", ((0, 0, 0), nrm, u), (25.5, 36.5), (-10.0, 1.5), base, c_extra)

    # D: reset (y = -5.72), looking from -Y
    ax = fig.add_subplot(gs[2, :])
    def d_extra(ax):
        gapmark(ax, (H.SW_C[0] + 1.6, H.Z_SW), (H.SW_C[0] + 1.6, H.Z_SW - H.S_PRE), f" {H.S_PRE:.2f} at rest", (0.1, 0))
        note(ax, (H.SW_C[0], H.Z_SW), "reset switch", (2.5, 1.3))
        note(ax, (21.5, H.Z_CI + H.SB_GAP + H.SB_T), f"spring arm ({H.mechanics()['reset flexure']['springboard_stiffness_N_per_mm']:.0f} N/mm)", (-9.5, 0.9))
        note(ax, (14.0, H.Z_BOT), "tongue (pressed from below)", (-5.5, 1.6))
    panel(ax, "D  Section y = -5.72: reset switch, plunger, spring arm and tongue", ((0, -5.72, 0), (0, -1, 0), (1, 0, 0)), (8, 30), (-9.6, -1.4), base, d_extra)

    # E: the same tongue, section y = -3.5 through the stop strip under the USB-C shell
    ax = fig.add_subplot(gs[3, 0])
    def e_extra(ax):
        gapmark(ax, (23.0, H.Z_USB_BOT), (23.0, H.Z_USB_BOT - H.G_STOP), f" stop gap {H.G_STOP:.2f}", (0.1, 0))
        note(ax, (21.0, H.Z_USB_BOT - H.G_STOP - 0.3), "thin strip lands on the shell", (-12, 1.15))
    panel(ax, "E  Section y = -3.5: overtravel stop under the USB-C shell", ((0, -3.5, 0), (0, -1, 0), (1, 0, 0)), (8, 30), (-9.6, -1.4), base, e_extra)

    # F: cover seen from below (slice 0.15 above its outer face)
    ax = fig.add_subplot(gs[3, 1])
    def f_extra(ax):
        note(ax, (22.6, 6.1), "press ring (reset)", (-14, 6))
        note(ax, (23.7, -5.7), "LED window", (-12, -6))
        note(ax, (1.6, -21.5), "buzzer ports 2 x 1.6", (-14, 6))
        ax.text(-29, -30.5, "seen from below: +Y points down", fontsize=6, color="#5c6a65")
    panel(ax, "F  Cover from below", ((0, 0, H.Z_BOT + 0.15), (0, 0, -1), (1, 0, 0)), (-31, 31), (-31, 31),
          [("cover", C, COL["cover"], 1)], f_extra)

    fig.suptitle("DiscTracker housing rev B: sections (true scale, mm). Frame: +Z toward the flight plate, z = 0 at the plate.",
                 fontsize=9, x=0.05, ha="left", y=0.93)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    fig.savefig(OUT, bbox_inches="tight")
    print("wrote", OUT)
