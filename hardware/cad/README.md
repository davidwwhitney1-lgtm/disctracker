# DiscTracker housing, rev B

A pod that clicks into a dock glued under each disc. To remove it, squeeze both latches and pull.
Built in CadQuery (`housing.py`); open the STEP files in SolidWorks.

![sections](renders/sections.png)

## Parts

| File (`out/`) | What |
|---|---|
| `pod.step/.stl` | Lid, wall, top ridge for the dock fingers, USB-C flat and port, two squeeze latches, three screw bosses |
| `cover.step/.stl` | Bottom cover: reset button, LED window with light shroud, buzzer chamber with two ports, battery cage, three screw columns |
| `dock.step/.stl` | Ring glued under the disc: flat key, four spring fingers, two latch windows |
| `jig_frame.step/.stl`, `jig_plunger.step/.stl` | Gluing jig: the frame centres itself on the disc rim, the plunger carries the dock to the plate |
| `housing_assembly.step` | Dock, pod and cover with the board, XIAO and battery in place |
| `report.json` | Every fit and gap (nominal, RSS, worst case), forces, strains, masses, balance, interference checks |
| `ref_*.stl` | Reference models for the viewer (board, parts, XIAO, battery, a generic driver) |

Renders are in `renders/`. `viewer/index.html` is the 3D viewer, and `sections.py` draws `renders/sections.png`.

## How it works

**Click in.** The flat next to the USB-C port lines up with a flat in the dock, so the pod only fits one way. Push the pod up into the dock:
- Four spring fingers in the dock ride over a ridge around the pod's top and snap under it (8 N).
- Their 40° faces pull the lid flat against the disc with about 2 N, so nothing rattles.
- At the same moment, both latch hooks snap into the dock's windows (9 N).

**Take out.** Press both latch hooks through the dock windows with thumb and finger (3.6 N each), then pull (about 14 N).
- The hooks are square, so they never let go on their own.
- If a landing pulls on the pod, it drops at most 0.5 mm onto the dock's sill. A shoulder in the ridge above each hook then takes the load off the latch arm.
- Pull-out strength is about 110 N, set by the sill, which is roughly 600 g on a 20 g pod.

**Reset button.** Press the ring on the cover. A flexible tongue in the cover carries a small spring arm (12 N/mm), and its plunger presses the XIAO's reset switch with about 3.8 N.
- After 0.63 mm of travel, a strip on the tongue lands on the XIAO's USB-C shell. Pressing harder never reaches the switch.
- The plunger and the stop both measure from the XIAO itself, so the XIAO's board thickness cancels out.

**Lights.** A 3.6 × 1.7 mm slot sits over the XIAO's red charge LED and its RGB status LED. A shroud stops 0.4 mm short of them and keeps the light from spilling into the pod.

**Buzzer.** The CPT-9019S sound hole is a 0.5 mm hole in one corner of the buzzer's face, so the cover makes a sealed chamber over the whole face, 0.3 mm short of touching it. Two 1.6 mm ports tune that chamber to about 4.3 kHz, close to the buzzer's 4 kHz tone.

**USB-C.** The opening is 13.1 × 7.2 mm with full radii. That follows Apple's case guideline (at least 12.45 × 6.6) plus 0.25 mm per side for print and position tolerance, so any cable's moulded plug fits up to the receptacle. Posts on the cover close the gaps beside the receptacle. You can charge with the pod in the disc.

**Board.** Three M2 × 6 countersunk screws go in from the lid, through the board's three alignment holes, into posts on the cover. They clamp the board between the lid's bosses and the cover's posts. The board never touches the wall (0.4 mm clearance), and four posts under the lid stop the lid from sagging onto the sensors.

## Key numbers

| | |
|---|---|
| Depth below the flight plate | **8.72 mm** (about 2.3 mm clear of an 11 mm driver rim) |
| Pod | 58.8 mm body, 61.4 mm over the ridge, 65.6 mm across the latches |
| Dock | 69 mm across |
| Mass, PA11 | pod 4.84 g, cover 2.92 g, dock 1.42 g (9.2 g), plus about 0.1 g of nylon screws |
| Balance | off-centre mass: pod (−3.2, 0.1) g·mm, cover (−1.1, 2.1) g·mm, dock (3.2, 0) g·mm. Pod and dock nearly cancel |

Stack, from the plate down (mm):

| Level | z (mm) |
|---|---|
| Lid top | 0 |
| Lid underside | −1.0 |
| Board top | −2.16 |
| Board bottom | −2.96 |
| XIAO component face | −4.26 |
| Cover inner face | −7.72 |
| Pod bottom | −8.72 |

## Tolerances and gaps

The printed features are taken as ±0.1 mm. MJF nylon holds about ±0.2 mm on a diameter, and JLC quotes ±0.3 mm as its worst case. Each fit is checked three ways:
- at nominal;
- statistically (RSS, the usual way to qualify a part);
- at the absolute worst case, with every tolerance stacking the same way.

All of them are in `report.json` and on the viewer page. As a robustness check, the RSS run is repeated at ±0.2 mm.

| Fit class | Gap |
|---|---|
| Locating fits (pod ridge to dock, flat key, latch hook to window) | 0.30 mm |
| Board edge to pod wall (the screws locate the board, never the wall) | 0.40 mm |
| Slots around anything that flexes; gaps between features of one part (MJF won't fuse them) | 0.60 mm |
| Cover to wall (visible reveal, chamfered both sides) | 0.20 mm |
| Lid to sensor chips / cover to USB-C shell | 0.30 / 0.25 mm |

Every fit passes at nominal and RSS, and still passes RSS at ±0.2 mm. Every fit except one passes at worst case too.

**The exception is the reset force.** Its worst case runs from 1.2 to 6.5 N, because the XIAO's reset switch height isn't published:
- the footprint says 0.53 mm;
- Seeed's 3D model shows 0.73 mm.

The design uses 0.62 ± 0.10 mm. Even at worst case the plunger can't hold the XIAO in reset (at most 1.3 N at rest, below the switch's 1.6 N). If your button doesn't click, raise the plunger with `S_PRE` (e.g. 0.20 to 0.12) or set `SW_H` to your measurement, then reprint the cover.

No housing part overlaps the board, XIAO, battery or buzzer models, and none overlaps Seeed's own XIAO STEP model (`python housing.py out --xiao-step <path>`). The only designed contact is the dock fingers' 0.5 mm preload on the ridge.

## Ordering and materials

- **Pod, cover, dock:** JLC3DP **PA11-HP (MJF)**. The flexures rely on its elongation (about 6.7 % allowed for repeated bending versus 2.7 % for PA12). PA12-HP fits every part, but the reset spring arm bends 4.4 % and would fatigue.
- **Jig:** PETG or PLA on a home printer; it's 226 mm across.
- **Wall thickness:**
  - All walls are at least 1.0 mm.
  - The only thinner sections are flexures, on purpose: the reset tongue's stop strip (0.57 mm) and the reset spring arm (0.9 mm).
  - Holes and slots are at least 1.6 mm.
  - The screw pilots are 3.6 mm deep so powder clears out.
- **Screws:** 3 × M2 × 6 countersunk (DIN 965 / ISO 7046), nylon or brass. Nothing steel near the magnetometer.
- **Tape for the dock:** 0.1–0.4 mm works; the fingers absorb the difference. Use 3M VHB 4914-025 (0.25 mm) with 3M 94 primer, or 3M 9495LE (300LSE, 0.17 mm). Disc plastic is low-energy, so primer or LSE tape is a must. Peel-test on a spare disc first.

## Assembly

1. Solder the battery leads to J1/J2, then tape the battery to the board (thin double-sided tape, 0.1 mm).
2. Set the pod lid-down on the table. Drop the board in, sensor face down, so its three holes sit over the lid bosses.
3. Lay the cover on top; its flat matches the pod's flat.
4. Turn it over and drive the three M2 × 6 screws in from the lid. Stop when they're snug: they cut their own threads in the posts.
5. Optional: put a 0.1 mm printed label over the reset tongue to seal its slot. A 10 × 10 mm closed-cell foam ring between the cover chamber and the buzzer makes it louder.

**Gluing a dock:**
1. Put the disc upside down.
2. Clean and prime the plate.
3. Put tape on the dock's top face.
4. Clip the dock onto the plunger's head, flat to flat.
5. Set the frame on the rim. Its three cone feet centre it on any disc from 205 to 219 mm.
6. Slide the plunger down until it touches the plate.
7. Press the dock's ring firmly for 30 s, then lift the jig off. The fingers let go of the plunger.

Let VHB cure for 24 h before throwing.

## Measure and adjust

- `XIAO_T` (1.25) is the XIAO board thickness. Seeed doesn't publish it; users measure 1.17–1.27 mm. Measure yours with calipers at the board edge.
- `SW_H` (0.62) is the reset switch height above the XIAO board, from the board face to the top of the button.
- After assembly, weigh the pod and spin-check the balance. Trim with solder on TP1–TP4 (r = 22 mm).
- Print one set and check the click before ordering more docks.

## Rebuilding

```
python housing.py out --xiao-step "path/to/XIAO-nRF52840 v15.step"   # STEP, STL, report.json (CadQuery 2.8)
python sections.py renders/sections.png                              # cross-section sheet
python viewer/bundle.py out viewer/models.json                       # mesh bundle for publishing the viewer
python3 board_parts.py ../kicad/disctracker_sensor.kicad_pcb board_parts.json   # after a PCB change (KiCad's Python)
```

## Limits

- **Not waterproof.** The USB-C opening, LED slot, buzzer ports and reset slot are open. Splash is fine; a dunk in a pond will reach the electronics. A conformal coat on the board is the cheap fix.
- **Untested in print.** The numbers are calculated: beam theory plus HP's PA11 data. Print a test set and check the click, the release force and the reset before relying on it.
