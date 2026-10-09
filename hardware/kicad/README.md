# DiscTracker sensor board — KiCad 9 project

Open `disctracker_sensor.kicad_pro` in KiCad 9.
- Schematic `disctracker_sensor.kicad_sch`: ERC 0 errors / 0 warnings.
- PCB `disctracker_sensor.kicad_pcb`: **DRC 0 violations, 0 unconnected, schematic parity clean** (all severities).
- Ready-to-order files in `fab/` (see "Ordering").

## Board
| | |
|---|---|
| Size | 56 mm round, flat at x = +26.5 mm for the USB-C plug |
| Stack | 4 layers, 0.8 mm: F.Cu signals + GND pour · In1 **solid GND plane (no signals)** · In2 +3V3 pour (4 short signal segments) · B.Cu signals + GND pour |
| Rules | 0.127 mm tracks (0.25 mm power), 0.12 mm clearance, vias 0.45/0.25 mm — within JLCPCB 4-layer standard |
| Sensor face (top, machine assembled) | U1–U6, C1–C11, R1–R9, JP1 |
| XIAO face (bottom, hand-soldered) | M1 XIAO, BZ1 buzzer, C12, J1/J2 battery pads, TP1–TP4 trim pads, battery outline |
| Not fitted (pair B) | U4, U5, C7–C10, R7, R8 |

Coordinates (origin = U1 = board center, +X toward the USB-C flat, seen from the sensor face):
U2/U3 at (±20.00, 0), U4/U5 at (0, ±20.00), U6 at (0, −25.0), XIAO center (+15, 0) with USB-C at the flat,
battery center (−6.54, 0), holes at r = 25.6 mm (30°/150°/250°), trim pads at r = 22 mm on the diagonals.

## Assembly notes
1. JLCPCB assembles the sensor face (`fab/bom_jlc.csv`, `fab/cpl_jlc.csv`). The LSM6DSV320X has no LCSC number:
   have JLC source it, or consign 3 chips. Check part rotations in JLC's placement preview (pin-1 dots).
2. Bridge **JP1 pads 2–3** (buzzer) with solder.
3. Solder the XIAO flat on the bottom by its castellated edges. Its underside **VBAT and GND pads are plated holes**
   on this board: from the sensor face, feed solder into the two holes next to the XIAO outline to join them.
4. Solder BZ1 and C12 on the bottom; battery leads to J1 (+) / J2 (−); bond the battery inside its silkscreen outline.
5. Weigh and spin-balance the finished pod; add solder to TP1–TP4 to trim.

## Ordering (JLCPCB)
- PCB: upload `fab/disctracker_sensor_gerbers.zip` — 4 layers, 0.8 mm, any color, "specify layer sequence" not needed.
- Assembly: top side, `fab/bom_jlc.csv` + `fab/cpl_jlc.csv`. Passives use JLC basic parts (confirm stock).
- Full parts list incl. hand-soldered parts: `fab/bom_all.csv`. Board-only STEP for the housing CAD: `fab/disctracker_sensor.step`
  (export again from your own KiCad with 3D libraries installed to include the parts).

## Known items
- Two vias sit under **U5** (not fitted on the first build). Move them before fitting pair B; U1–U4 have nothing under them.
- MMC5603NJ footprint (`Package_BGA:WLP-4_0.86x0.86mm_P0.4mm`): confirm ball pitch/pad size against MEMSIC's drawing.
- LGA-14 footprint vs ST TN0018 land pattern: KiCad's standard pattern for this package family.
- XIAO underside SWD/NFC pads are present as unconnected copper (footprint from Seeed's OPL library, CC BY-SA 4.0).

## How it was built (`gen/`)
1. `gen.py` — schematic + symbol library (don't re-run once you edit in KiCad; it also rewrites the .kicad_pro).
2. `xiao_fp.py` — XIAO footprint tweaks (plated VBAT/GND holes, outline on fab layer).
3. `pcb.py <dir> <netlist>` — placement, outline, planes, keepouts, silkscreen, locked GND fan-out under each IMU.
4. `route.py` — Freerouting 2.1 autoroute (In1 kept as a plane), then GND pours.
5. `stitch.py` — GND stitching vias (3 mm grid); `fixups.py` + `padvia.py` — hand fixes for this route; `check_gnd.py` — GND connectivity check.
6. `fab.sh` + `jlc.py` — DRC, Gerbers, drills, pick-and-place, BOMs, STEP, renders.
Autorouting isn't deterministic, so `fixups.py` only applies to the committed route. From here on, edit the PCB in KiCad.
