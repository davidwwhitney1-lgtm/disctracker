# DiscTracker housing (rev A)

Click-in pod + glued dock, built in CadQuery (`housing.py`). Open the STEP files in SolidWorks.

| File (`out/`) | What |
|---|---|
| `pod.step/.stl` | Pod: lid, wall, click ridge, USB-C opening, key tab, 3 standoffs + pins for the PCB |
| `cover.step/.stl` | Snap-in floor cover: buzzer sound hole, XIAO LED window, fingernail notch |
| `dock.step/.stl` | Dock ring (glued to the disc) with 3 snap arms and the key notch |
| `jig.step/.stl` | Gluing jig: sits on the upturned disc's rim, holds the dock centered (print flat) |
| `housing_assembly.step` | Everything assembled with a simplified PCB, XIAO, battery and buzzer |
| `report.json` | Height, snap numbers, masses, interference check (empty = no clashes) |

Viewer: `viewer/index.html` (three.js) - renders in `renders/`.

## Key numbers
- 7.5 mm below the flight plate; pod 58.4 mm (59.6 over the ridge); dock 66 mm.
- Snap: 0.45 mm hook engagement, ~2.3 % arm strain (fine for PA12 / PETG). Near-flat catch face: the pod
  should not shake loose; remove by easing each arm out at its lip.
- Mass in PA12: pod 3.3 g, cover 1.5 g, dock 1.0 g (5.8 g). PETG: 7.3 g.

## Assembly
1. Board into the pod, sensor face toward the lid, pins through the board's three holes; melt or glue the pin tips.
2. Foam pad on the battery, click the cover in (bumps into the wall dimples).
3. Glue the dock: 3M 94 primer + VHB, using the jig (set `DISC_OD`, `RIM_TO_PLATE` per disc mould).
4. Line up the pod's tab with the dock's notch and push until all three arms click.

## Open items
- Weigh vs target: options to cut ~1.5 g - pocket the lid between the sensors (the plate covers it when installed),
  0.5 mm cover, PA12 at 0.7 mm wall.
- Confirm the XIAO LED window position on your board.
- Print a PETG test set first; tune `HOOK_IN` (snap strength) and `DOCK_RI` (fit) if needed.
