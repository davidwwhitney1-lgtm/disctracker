# DiscTracker sensor board — KiCad 9 project

Open `disctracker_sensor.kicad_pro` in KiCad 9. One A3 sheet: `disctracker_sensor.kicad_sch`
(PDF copy: `disctracker_sensor.pdf`). ERC: 0 errors, 0 warnings (KiCad 9.0.9).

## What's in it
| Block | Parts |
|---|---|
| MCU | M1 XIAO nRF52840 Sense (SMD footprint), R3 33 Ω SPI clock series, C12 10 µF |
| Motion | U1–U5 LSM6DSV320X on shared SPI, CS1–CS5, C1–C10 100 nF (VDD + VDDIO), R4–R8 100 k CS pull-ups |
| Magnetometer | U6 MMC5603NJ on I²C (D4/D5), C11 2.2 µF, R1/R2 4.7 k |
| Buzzer | JP1 3-pad jumper on D6 (1-2 = U5 CS, 2-3 = buzzer), R9 100 Ω, BZ1 CUI CPT-9019S |
| Power | BT1 Adafruit 1317 (schematic only, not on board), J1/J2 battery solder pads, PWR_FLAG |
| Mechanical | TP1–TP4 balance trim pads, H1–H3 2.1 mm alignment holes |

**DNP (pair B, fit later):** U4, U5, C7–C10, R7, R8. **Ship JP1 bridged 2-3.**
Pin numbers follow ST DS14623 Rev 1 (LSM6DSV320X) and the MMC5603NJ datasheet; nets match `../pinmap.csv`.

## Libraries
- `disctracker.kicad_sym`: LSM6DSV320X, MMC5603NJ (pinout identical to KiCad's MMC5633NJL), XIAO_nRF52840_Sense_SMD.
- `disctracker.pretty/XIAO-nRF52840-SMD.kicad_mod`: from Seeed Studio's OPL KiCad library
  (https://github.com/Seeed-Studio/OPL_Kicad_Library), licensed CC BY-SA 4.0.
- Everything else uses KiCad 9's standard libraries.

## Still to check during layout
- MMC5603NJ footprint uses `Package_BGA:WLP-4_0.86x0.86mm_P0.4mm`: confirm ball pitch/pad size against MEMSIC's drawing.
- LGA-14 footprint vs ST TN0018 land pattern.
- XIAO face parts (M1, BZ1, C12, J1/J2, TP1–TP4) go on the back side; sensor face is machine assembled.

## Regenerating
`gen/gen.py` built this schematic (`python3 gen/gen.py <outdir> <path to Seeed XIAO-nRF52840-SMD.kicad_mod>`).
Once you edit the schematic in KiCad, treat the `.kicad_sch` as the source and stop regenerating.

## Layout rules (next step)
- Board origin at U1; U2/U3 centers at (±20.00, 0), U4/U5 at (0, ±20.00), all the same rotation (see `../placement.csv`).
- 56 mm round, 4 layers, 0.8 mm; solid ground plane under the sensors.
- U6 at (0, −24), ≥ 10 mm from XIAO, battery, buzzer and current traces on either face.
- Holes H1–H3 at r = 25.6 mm, 30° / 150° / 250°.

## Pre-fab checklist
- [x] Datasheet pin check; ERC clean
- [x] pinmap.csv matches schematic
- [ ] DRC clean; chip centers verified vs placement.csv
- [ ] BOM/CPL exported with DNP marked; LCSC/consign status for U1–U5
- [ ] Gerbers reviewed in a viewer; weight and balance estimate
