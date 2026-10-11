# Housing brief: dock + pod

Every disc gets a **dock** glued under the flight plate. One **pod** (board, XIAO, battery) clicks into any dock.
The current design is **rev B**; the CAD, fit report and assembly steps are in `cad/README.md`.

## Decisions
- **Click in, squeeze to release.** Spring fingers in the dock snap over a ridge on the pod and hold it flat against the
  plate with no rattle. Two square latch hooks lock into windows in the dock; press them through the windows to remove the pod.
  A flat by the USB-C port keys the pod one way round.
- **Glued dock.** 3M VHB 4914-025 with 3M 94 primer, or 3M 9495LE (300LSE). The printed jig centres the dock on the disc rim.
- **Sensor face up against the plate.** The XIAO, battery and buzzer face the cover, where the reset button, LED window and
  buzzer ports are.
- **Material.** JLC3DP PA11-HP (MJF) for the pod, cover and dock; the flexures need its elongation.
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

The shallowest drivers have about 11 mm of rim depth (putters 12-16 mm), which leaves about 2.3 mm.

## Loads
- Release spin-up: about 0.02 N·m on the pod. A tree hit that stops a 2,500 rpm spin: about 0.35 N·m, carried by the
  latch hooks in the dock windows.
- Pull-out (rim-down landing): the square latch hooks and the dock sill hold about 110 N, roughly 600 g on a 20 g pod.
- Centring: the dock fingers hold the pod repeatably in its dock. Each 0.1 mm the dock is off the spin axis gives about
  0.7 g of bias on U1 at 2,500 rpm, which the spin pair cancels and the firmware calibrates per disc.
