# KiCad project plan (KiCad 9)

Create the project here as `disctracker_sensor.kicad_pro`.

## Libraries
- Seeed XIAO footprint from https://github.com/Seeed-Studio/OPL_Kicad_Library (use the SMD variant with battery pads).
- LSM6DSV320X (LGA-14) and MMC5603NJ: build from the datasheet land patterns; check ST/Ultra Librarian first.

## Schematic sheets
1. `power` - XIAO 3V3, BAT pads, C12, decoupling
2. `imu` - U1-U5, CS pull-ups, R3, INT1; DNP flag on U4/U5/C7-C10
3. `mag_buzzer` - U6, R1/R2/C11, buzzer + driver (per open decision 1)

## Layout rules
- Chip **centers** exactly at placement.csv coordinates; set the board origin at U1; all chips identical rotation.
- 4 layers, 0.8 mm; solid ground under sensors.
- U6 >= 10 mm from battery leads, charger, USB, buzzer, steel.
- Balance: mirror every off-center mass; add trim pads opposite anything off-center. Center mark/hole for alignment.
- CS lines idle high so DNP/unpowered footprints don't float.
- Add the board outline to the same 20 mm arm geometry; size is set by arms + XIAO (21 x 17.8 mm).

## Pre-fab checklist
- [ ] Datasheet pin check (open decision 4); ERC clean
- [ ] Pin conflict resolved; pinmap.csv matches schematic
- [ ] DRC clean; chip centers verified vs placement.csv
- [ ] BOM/CPL exported with DNP marked; LCSC/consign status for U1-U5
- [ ] Gerbers reviewed in a viewer; weight and balance estimate
