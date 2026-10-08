# Housing brief: dock + pod

Every disc gets a **dock** glued under the flight plate. One **pod** (board + XIAO + battery) twists into any dock.
Numbers are first estimates; finalize the pod around the KiCad STEP export.

## Height budget (below the flight plate)
| Layer | mm |
|---|---|
| VHB tape | 0.25 |
| Dock ring | 0.8 |
| Pod lid | 0.6 |
| Sensors (LSM6DSV320X, datasheet) | 0.83 |
| Sensor PCB | 0.8 |
| XIAO incl. USB-C (measure) | ~4.2 |
| Pod floor | 0.6 |
| **Total** | **~8.1** |

Shallowest drivers have ~11 mm rim depth (putters 12-16 mm), so ~3 mm clearance.

## Dock (one per disc), target <= 1.5 g
- Flat ring ~66 mm OD, ~50 mm ID, 0.8 mm thick; glue face flat or matched to the plate dome.
- 3 bayonet lugs at r ~30-33 mm, 2.6 mm tall with inward lip; one lug ~14 deg wider (key).
- Detent notch in each lip; "front" arrow.
- Bond with 3M VHB + 3M 94 primer (disc plastics are low-surface-energy); peel-test on a spare disc.

## Pod
- ~58 mm OD, ~7 mm tall; 0.6 mm lid/floor, 0.8 mm wall; translucent print so the XIAO LED shows.
- 3 top-edge tabs matching the lugs, each with a detent bump; grip ribs.
- USB-C notch at "front"; sound hole under BZ1.
- Board located by 3 pins through its alignment holes (r = 25.6 mm at 30/150/250 deg), then bonded/potted.
  Battery bonded (it sees ~110 g at 2,500 rpm).

## Centering jig
- Ring that sits on the disc's outer edge (~210-213 mm) with 3 flexible fingers; center cup holds the dock while glue cures.
- Target +/-0.3 mm. Each 0.1 mm off-center = ~0.7 g bias on U1 at 2,500 rpm (spin pair unaffected; firmware calibrates it per disc).
- Mark to align "front" with the disc stamp.

## Loads (calculated)
- Release twist: ~0.02 N*m. Impact: 12 g pod x 1,000 g = ~120 N axial.
