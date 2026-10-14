# Housing brief: dock + pod

Every disc gets a **dock** glued under the flight plate. One **pod** (board, XIAO, battery) twists into any dock.
The current design is **rev C**, built for a Bambu P1S printing PETG; the CAD, fit report, print settings and assembly steps are in `cad/README.md`.

## Decisions
- **Twist to lock, with clicks.** Three lugs go up through notches in the dock, and a 30° clockwise turn (seen from below) puts them over a solid lip.
  - Helical ramps pull the lid tight against the plate.
  - Spring pawls in the dock click over racks on the pod every 3°, so it can't unscrew.
  - The wide lug keys the pod one way round.
  - Turn it back to remove it.
- **Why not a snap fit.** Rev B's push-in snap (fingers and squeeze latches) needed MJF nylon. In PETG it was loose, didn't click and broke.
  - Rev C holds the pod by geometry, so print tolerance only changes how far it turns.
  - Its only springs bend less than 1 %, along the print layers.
- **Glued dock.** 3M VHB 4914-025 with 3M 94 primer, or 3M 9495LE (300LSE). The printed jig centres the dock on the disc rim.
- **Sensor face up against the plate.** The XIAO, battery and buzzer face the cover, where the reset pinhole, LED window and buzzer ports are.
- **Material.** PETG on the P1S, no supports. Optionally nylon or ASA. Or order the `--process mjf` build in PA11 from JLC3DP.
- **No magnets or steel.** The magnetometer is 9 mm from the nearest screw, so the screws are nylon or brass.

## Height budget (below the flight plate)
| Layer | mm |
|---|---|
| Pod lid | 1.0 |
| Lid to sensors | 0.3 |
| Sensors (LSM6DSV320X, max) | 0.86 |
| Sensor PCB | 0.8 |
| XIAO incl. USB-C (Seeed STEP: 1.25 board + 3.21 receptacle + solder) | 4.51 |
| Cover clearance + cover | 1.25 |
| **Total** | **8.72** |

The shallowest drivers have about 11 mm of rim depth (putters 12-16 mm), which leaves about 2.3 mm. The dock is 4.85 mm deep, inside the pod's depth.

## Loads
- **Release spin-up:** about 0.02 N·m on the pod.
- **Tree hit that stops a 2,500 rpm spin:** about 0.35 N·m. The ratchet alone holds at least 0.37 N·m (at low friction), and about 0.78 N·m with the clamp after a normal twist.
- **Pull-out (rim-down landing):** the lugs over the lip hold about 315 N, roughly 1,600 g on a 20 g pod. The tape lets go first, at about 270 N.
- **Centring:** the dock's 59.4 mm bore centres the pod within 0.3 mm. Each 0.1 mm the dock is off the spin axis gives about 0.7 g of bias on U1 at 2,500 rpm, which the spin pair cancels and the firmware calibrates per disc.
