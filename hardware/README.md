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
- 5 LSM6DSV320X footprints (center + 2 pairs at 20 mm), **build with 3** (center + pair A); U4/U5 DNP.
- SPI, one CS per IMU; MMC5603NJ magnetometer on I2C.
- 4 layers, 0.8 mm, solid ground plane; all chips same orientation; non-magnetic piezo.

## Open decisions
1. **Buzzer pin.** D0-D10 are all used (3 SPI + 5 CS + INT1 + 2 I2C). Proposed: buzzer on D6 (CS5) via a 3-pad
   solder jumper, valid while U5 is DNP. If pair B is ever fitted, no buzzer on this board. Alternatives: drop INT1
   and poll, or an I2C expander. Step-2 (Raytac MDBT50Q) board removes the limit.
2. **Board shape:** round ~48 mm vs "+" cross with ~7 mm arms (~1 g vs ~2.5 g).
3. **16 MB flash (W25Q128):** recommended, but needs another CS (pin pressure) - likely step 2.
4. **Verify in the LSM6DSV320X datasheet:** pin numbers, high-g full-scale options, tie-offs for OCS_Aux / SDx / SCx.
5. **Sourcing:** LSM6DSV320X stock is patchy; check JLCPCB, else consign.
