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

## Decided
- Spin to 2,500 rpm; keep the Bluetooth RSSI finder (UWB, GPS, Channel Sounding dropped).
- **48 mm round board**, 4 layers, 0.8 mm, solid ground plane.
- 5 LSM6DSV320X footprints (center + 2 pairs at 20.00 mm), **build with 3** (center + pair A); U4/U5 DNP.
- SPI, one CS per IMU; MMC5603NJ magnetometer on I2C.
- **Buzzer on D6** through 3-pad jumper JP1 (A = U5 CS, B = buzzer); non-magnetic piezo.
- **No extra flash on step 1** - at the new board's ~113 KB/s, 16 MB holds only ~48 throw windows; revisit on step 2.
- **Sensors on one face, XIAO hand-soldered on the other** (a flat-soldered XIAO leaves no room for U1 under it).
  Center alignment hole replaced by 3 holes on a 22 mm circle.

## Datasheet check
- MMC5603NJ (Rev. B datasheet, confirmed): A1 GND, A2 SCL, B1 VDD, B2 SDA; 1.62-3.6 V; **>= 2.2 uF** bypass
  (C11 changed from 1 uF); I2C 0x30; 1 kHz only with hpower=1; keep away from current traces on either face and from the battery.
- LSM6DSV320X (from Zephyr bindings; ST PDF blocked from the build container - re-verify): accel 2-320 g incl. 256 g,
  high-g ODR 480-7680 Hz, gyro up to 4000 dps (667 rpm).
- Still needed from the ST PDF: LGA-14 pin numbers + land pattern, SDx/SCx/OCS_Aux tie-offs in SPI mode, SPI max clock.

## Open
1. LSM6DSV320X pinout/footprint (above).
2. Magnetometer position vs XIAO charger / battery traces (needs XIAO footprint details).
3. Piezo part and whether Q1 driver is needed.
4. Balance trim-pad sizes (needs a mass map), battery size/runtime.
5. Housing: weight (closed 1 mm shell ~6-9 g; target 3-5 g), rim clearance (~15.6 mm stack), USB-C/LED/sound openings.

See `overview.html` for wiring, board layout and housing diagrams with confidence tags.
