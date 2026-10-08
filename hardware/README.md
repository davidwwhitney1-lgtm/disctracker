# DiscTracker custom PCB (sensor board, step 1)

Organized from `docs/PROJECT_CONTEXT.md` section 3 (that doc and the datasheets win over anything here).

**Goal:** measure spin up to 2,500 rpm. The XIAO's LSM6DS3TR-C gyro saturates at 2000 dps (333 rpm), so
we add a differential "spin pair" of high-g accelerometers at r = 20 mm: omega = sqrt((a1 - a2) / 2r).
The XIAO nRF52840 Sense is soldered flat on top and keeps BLE, charging and firmware.

## Files
| File | Contents |
|---|---|
| `bom.csv` | Parts, quantities, populate/DNP |
| `placement.csv` | Chip centers (mm from U1) and DNP status |
| `pinmap.csv` | XIAO pin to net to part |
| `kicad/README.md` | KiCad project setup, sheet plan, layout rules, pre-fab checklist |

## Decided / recommended (revision 2)
- **Dock + pod housing**: a light dock glued under every disc; one pod twists in/out (keyed quarter turn). See `housing.md`.
- **56 mm round board** (was 48), 4 layers, 0.8 mm (0.6 mm or cutouts to save weight). Pod ~8 mm tall vs ~11 mm shallowest rim.
- Sensors on one face (factory assembled), XIAO + battery + buzzer on the other (hand-soldered).
  U1 stays at the exact center; the XIAO only computes, so its position doesn't affect the measurements.
- **XIAO shifted to ~+15 mm** so USB-C reaches the pod edge (charge/flash in place); battery opposite at ~-18 mm for balance.
- Spin pairs at 20.00 mm; U4/U5 DNP. Magnetometer at (0, -24).
- Buzzer CUI CPT-9019S on D6 via JP1. 100 k CS pull-ups R4-R8.
- No extra flash on step 1.

## Datasheets (checked)
- LSM6DSV320X (ST DS14623 Rev 1): pins 1 SDO, 2 SDx, 3 SCx, 4 INT1, 5 VDDIO, 6-7 GND, 8 VDD, 9 INT2, 10 OCS_aux,
  11 SDO_aux, 12 CS, 13 SCL/SPC, 14 SDA/SDI. SDx/SCx -> GND; INT2/OCS_aux/SDO_aux unconnected. VDD 1.71-3.6 V,
  SPI <= 10 MHz, high-g +/-32..320 g at 480-7680 Hz, gyro <= 4000 dps, 2.5x3.0x0.83 mm, ~0.9 mA. Land pattern: TN0018.
  Firmware: set I2C_I3C_disable (IF_CFG 03h) on every chip first.
- MMC5603NJ: A1 GND, A2 SCL, B1 VDD, B2 SDA; >= 2.2 uF; I2C 0x30; keep away from current traces on both faces and the battery.
- XIAO nRF52840: charger BQ25101, 50 mA default (100 mA option) -> battery >= 50 mAh.

## Before KiCad
1. Measure XIAO height (incl. USB-C) and weight. (you)
2. Measure rim depth / inside rim diameter of your shallowest driver; disc weights. (you)
3. Choose battery: ~3 mm thick, >= 50 mAh, protected, <= 15x20 mm. (you; I can shortlist)
4. Confirm: 56 mm board, XIAO at +15 mm with edge USB-C, dock + twist-lock pod. (you)
5. Seeed XIAO SMD footprint; LGA-14 footprint vs TN0018; JLCPCB footprints for MMC5603NJ / CPT-9019S; LSM6DSV320X stock. (me, part of KiCad work)

See `overview.html` for diagrams with confidence tags.
