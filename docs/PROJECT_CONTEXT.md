# DiscTracker – Project Context (handoff file)

Written 2026-10-08 so that other Claude threads (e.g. the one doing the **custom PCB / KiCad** work) have
everything learned so far. Owner: David Whitney (Messiah University engineering). If something here
conflicts with a datasheet, **the datasheet wins** – several numbers below are engineering estimates and are marked as such.

---

## 1. What the project is

A disc golf flight tracker that sits under the flight plate of a disc. It records each throw
(**speed, spin, hyzer, nose, launch angle, wobble** – the six TechDisc numbers) and sends it over
Bluetooth LE to a website (this repo, GitHub Pages) opened on an iPhone in the **Bluefy** browser,
or Chrome on a PC. The website also has a live 3D view, a Bluetooth hot/cold disc finder, calibration,
power control, a flight simulator, and (new) full raw-data recording.

**Current hardware (prototype):** Seeed **XIAO nRF52840 Sense** + small LiPo, mounted at the disc center.
- IMU: on-board **LSM6DS3TR-C** (internal I²C bus Wire1), gyro **±2000 dps**, accel **±16 g**, FIFO at **416 Hz**.
- **2000 dps = 333 rpm**, so the gyro saturates on real drives. This is the core limitation the custom PCB fixes.
- 2 MB QSPI flash (Puya P25Q16H, JEDEC 85 60 15) – now used as a raw-data recorder.
- Firmware: Arduino, Seeed nRF52 core 1.1.13, Adafruit Bluefruit. Builds to ~172 KB.

## 2. Repo / file locations

| What | Where |
|---|---|
| Website (published) | this repo, `index.html` → GitHub Pages |
| Firmware (canonical) | local: `OneDrive - Messiah University\1. MESSIAH UNIVERSITY CLASS FILES\Disc_tracker\disc_tracker_v2\` (`disc_tracker_v2.ino`, `lsm6ds3tr_c.h`, `throw_metrics.h`, `flash_log.h`) – **not in this repo** |
| PC analysis tool | local: `Disc_tracker\analysis\disclab.py` |
| Firmware binaries | local: `Disc_tracker\build\` (`.uf2`, `.zip`, `.hex`) |
| Explainer doc | Claude Doc "DiscTracker: How Everything Works" (12 sections, diagrams) |

---

## 3. CUSTOM PCB – everything decided so far  ⭐ (most relevant for CAD)

### 3.1 Requirements / decisions
| Requirement | Decision |
|---|---|
| Spin range | **up to 2,500 rpm** (41.7 rev/s) |
| Disc finder | **Keep the Bluetooth RSSI hot/cold finder.** UWB / GPS / Channel Sounding were evaluated and **dropped** (not critical; UWB would need a native iPhone app + Mac). |
| Spin sensing above gyro range | **Differential "spin pair"** of high-g accelerometers at a known radius |
| Spin-pair radius | **20 mm** from center (user chose 20 mm over 5 mm; bigger signal, less placement sensitivity) |
| Architecture (step 1) | A **sensor board** with the **XIAO soldered flat onto it** via its castellated pads (no loose wires at 2,500 rpm). XIAO keeps doing BLE, battery, charging, firmware. |
| Architecture (step 2, later) | Single board with a BLE module (Raytac MDBT50Q nRF52840) instead of the XIAO, ~28–40 mm round |
| Populating | **"Design for 5, build with 3"**: 5 sensor footprints (center + 2 pairs), assembler fits **center + one pair**, other two marked DNP |
| Buzzer | Wanted (piezo, **not magnetic** – a magnet would ruin the magnetometer) on a spare pin – see pin conflict note 3.4 |
| Board shape | **Not decided yet**: round ~48 mm, or "+" cross with ~7 mm arms (lighter, ~1 g vs ~2.5 g). Add a center mark/hole for alignment. |
| Data memory | Recommended to add a bigger flash on the final board (16 MB **W25Q128** ≈ 50 min of full-rate recording; 128 MB W25N01G ≈ 6.5 h) |

### 3.2 Why a spin pair (the physics)
- Each sensor at radius r feels centripetal **ω²r** outward; the two sensors point opposite ways.
- Both feel the **same** linear acceleration (pull, drag, gravity) → **subtracting cancels it**:
  **ω = √((a₁ − a₂) / 2r)**. Adding them gives clean center linear acceleration.
- Works **during the pull** (current single-chip method only works in free flight).
- If the board is off the spin axis by δ, sensors are at r+δ and −r+δ → difference is still 2rω² (**cancels**).
- Sensors on the X axis feel r(ωz² + ωy²): wobble leaks in slightly; corrected by the center gyro (1 pair) or solvable from accelerometers alone (2 pairs).
- At **20 mm**: 2,500 rpm → **140 g** per sensor, + ~20 g pull ≈ **160 g** → set high-g range **±256 g**. At 300 rpm: 2 g per sensor, 4 g difference. 0.1 mm placement error ≈ 0.25% spin error. rpm = 9.55·√(a/r).
- 1 pair vs 2 pairs: 1 pair gives ~90% of the benefit. 2nd pair adds self-checking, redundancy, ~30% less noise, wobble without the gyro.

### 3.3 Parts (sensor board, step 1)
| Ref | Part | Qty | Package | Job |
|---|---|---|---|---|
| U1 | **ST LSM6DSV320X** | 1 | LGA-14, 2.5 × 3.0 × 0.86 mm | **Center** sensor: gyro ±4000 dps, accel ±16 g **and** high-g ±32…320 g channel |
| U2, U3 | **ST LSM6DSV320X** | 2 | LGA-14 | Spin pair A at (+20, 0) and (−20, 0) mm – **populated** |
| U4, U5 | **ST LSM6DSV320X** | 2 | LGA-14 | Spin pair B at (0, +20) and (0, −20) mm – **DNP initially** |
| U6 | **MEMSIC MMC5603NJ** | 1 | WLCSP 0.8 × 0.8 mm | Magnetometer, up to 1 kHz (rotation angle / spin cross-check). JLCPCB part **C404328** |
| C1–C10 | 100 nF 0402 | 10 | 0402 | 2 per LSM6DSV320X (VDD, VDDIO) |
| C11 | 1 µF 0402 | 1 | 0402 | Magnetometer decoupling |
| C12 | 10 µF 0603 | 1 | 0603 | Bulk at the XIAO 3V3 connection |
| R1, R2 | 4.7 kΩ 0402 | 2 | 0402 | I²C pull-ups for the magnetometer |
| R3 | 33 Ω 0402 | 1 | 0402 | Series resistor on SPI clock (20 mm runs) |
| — | XIAO nRF52840 Sense footprint | 1 | castellated SMD | XIAO soldered flat on top, centered over U1 |
| — | BAT+/BAT− pads | 2 | pads | Battery |
| — | Piezo buzzer (+ driver transistor if needed) | 1 | small SMD | Finder |

Alternative for U2–U5: **ST H3LIS331DL** (3×3 mm, accel-only, ±100/200/400 g) – cheaper but two part types; recommendation is all five LSM6DSV320X.
**Verify against the LSM6DSV320X datasheet**: exact pin numbers, the high-g full-scale options, and how the auxiliary pins (OCS_Aux, SDx, SCx) must be tied/left open. INT2 on U2–U5 unused.

### 3.4 Pin map (XIAO → sensor board)
| XIAO pin | Connects to | Purpose |
|---|---|---|
| 3V3 | VDD + VDDIO of U1–U5, VDD of U6, R1/R2, C12 | Power |
| GND | all GND + ground plane | Ground |
| **D8** (SCK) | via R3 → SCL/SPC of U1–U5 | SPI clock |
| **D10** (MOSI) | SDA/SDI of U1–U5 | SPI data out |
| **D9** (MISO) | SDO/SA0 of U1–U5 | SPI data in |
| D0 | CS U1 (center) | chip select |
| D1 | CS U2 (+X) | chip select |
| D2 | CS U3 (−X) | chip select |
| D3 | CS U4 (+Y) | chip select (DNP at first) |
| D6 | CS U5 (−Y) | chip select (DNP at first) |
| D7 | INT1 of U1 | data-ready → read all sensors at the same instant |
| D4 (SDA) | U6 SDA + R1 | magnetometer I²C |
| D5 (SCL) | U6 SCL + R2 | magnetometer I²C |
| BAT+/BAT− | XIAO underside battery pads → board pads | battery |

- Five identical LSM6DSV320X can't share I²C (only 2 addresses) → **SPI with one CS each**, ~1.9 kHz for all five.
- **⚠ Open pin conflict:** with all 5 CS lines + INT1, **every XIAO pin D0–D10 is used** → no pin for the buzzer.
  Options: (a) buzzer on D3 or D6 while pair B is DNP (route both via a solder jumper), (b) drop the INT1 data-ready line
  and poll, (c) put the buzzer on the magnetometer's I²C via a tiny I/O expander. Needs a decision in the schematic.
- The XIAO's **built-in LSM6DS3TR-C stays on its internal bus** and keeps doing wake-on-motion for the power modes.
- CS lines need to idle high (pull-ups or firmware sets them high before SPI starts) so DNP footprints/unpowered states don't float.

### 3.5 Layout rules
```
                  U4 (0, +20.00 mm)
                        │
   U3 (−20.00, 0) ──── U1 (center) ──── U2 (+20.00, 0)     all five chips in the SAME orientation
                        │     U6 magnetometer ~8–10 mm off center,
                  U5 (0, −20.00 mm)   away from battery leads / charger / USB
        XIAO on top, centered over U1. Battery centered under the board.
```
- Chip **centers** exactly at (±20.00, 0) and (0, ±20.00) mm from U1 (measure to the die/package center, not the board edge).
- **All chips same orientation** (not rotated) so the X-difference of pair A and Y-difference of pair B give 2ω²r directly.
- 4 layers, **0.8 mm** thick, solid ground plane under the sensors.
- Magnetometer ≥10 mm from battery leads, the XIAO charger, USB connector, buzzer, and any steel.
- **Balance:** every off-center mass mirrored; small copper **balance pads** opposite anything off-center (add solder to trim). Imbalance force scales with rpm² (6× worse at 2,500 than 1,000 rpm).
- Strain relief: board + battery fixed with VHB and potting; nothing may shift at 2,500 rpm.
- Board size is set by the 20 mm arms + XIAO (21 × 17.8 mm), not by the sensors.

### 3.6 Weight / cost (estimates)
- Sensor board ~1–2.5 g, chips + caps ~0.1 g, XIAO ~3 g, battery ~3 g → **≈ 7–9 g total**. Use a ~165 g disc so the total ends near normal weight.
- Cost per tracker (batch of 5, all 5 sensors): **≈ $75–80**. LSM6DSV320X ≈ $6.74 each (DigiKey; ST eStore ≈ $5.33 @500) is ~half the cost. Center + 1 pair saves ~$13.
- **LSM6DSV320X stock is patchy** (DigiKey showed 0 stock / 24-week lead; ST eStore and Farnell had stock). If JLCPCB doesn't stock it, use consigned parts. Eval board: **STEVAL-MKI251A**.

### 3.7 Useful links
- LSM6DSV320X: https://www.st.com/en/mems-and-sensors/lsm6dsv320x.html · datasheet https://www.st.com/resource/en/datasheet/lsm6dsv320x.pdf · ST eStore https://estore.st.com/en/lsm6dsv320xtr-cpn.html
- MMC5603NJ datasheet: https://www.espruino.com/files/MMC5603NJ.pdf · JLCPCB https://jlcpcb.com/partdetail/C404328
- Seeed XIAO in your PCB: https://www.seeedstudio.com/blog/2022/08/19/how-to-use-seeed-studio-xiao-in-your-pcb-design/
- Seeed KiCad library (XIAO footprint incl. SMD w/ battery pads): https://github.com/Seeed-Studio/OPL_Kicad_Library
- XIAO KiCad library fix guide (.pretty folder, set footprint to SMD): https://fabacademy.org/2026/labs/zoi/xiaolibfix.html
- KiCad 9: https://www.kicad.org/download/ · JLCPCB / PCBWay for fab + assembly
- Raytac MDBT50Q (step-2 BLE module): https://cdn.sparkfun.com/assets/4/7/4/3/8/_nRF52840__MDBT50Q-1MV2___MDBT50Q-P1MV2_Ver.K_spec.pdf

### 3.8 Firmware plan for the new board (not written yet)
1. SPI driver for up to 5 × LSM6DSV320X: high-g ±256 g, ~1.9 kHz, all read on U1's data-ready.
2. MMC5603 driver, continuous 1 kHz on D4/D5.
3. Spin pairs: pair A from X difference, pair B from Y difference, cross-checked/averaged.
4. Fusion: gyro (≤667 rpm at ±4000 dps) + spin pair + magnetometer → orientation survives hard pulls → fixes speed/angle errors.
5. Website live readout of gyro / pair A / pair B / magnetometer side by side for tachometer bench tests.

### 3.9 Expected accuracy (estimates, not yet measured)
| | Current, gentle (<333 rpm) | Current, hard drive | New PCB |
|---|---|---|---|
| Spin | ±1–2% | ±3–10%, sometimes none | ±1–2% to 2,500 rpm |
| Speed | ±5% | ±10–25% (reads low) | ±3–5% |
| Launch | ±2–4° | ±5–15° | ±2–4° |
| Hyzer/Nose | ±3–5° | ±5–15° | ±2–4° |
| Release timing | ±2.4 ms | ±2.4 ms | ±0.5 ms |
Plan: side-by-side test (both trackers on one disc) with radar gun, laser tachometer, slow-mo video.

### 3.10 Rejected options (don't re-propose without reason)
- **UWB (Qorvo DWM3001C)** for 1-ft finding – needs a native iPhone app (Nearby Interaction) + Mac; user said not critical.
- **GPS (u-blox MAX-M10S)** – ~1.5 m accuracy, adds 3–5 g and power; dropped.
- **Bluetooth Channel Sounding (nRF54L15)** – no iPhone support.
- Homemade accelerometer – not practical. Bosch BMA530 (smallest, 1.2×0.8 mm) – only ±16 g.
- microSD – heavy, off-center, can pop loose.
- Magnetic buzzer – ruins magnetometer.
- Adafruit breakout prototype (ADXL375 ×2 at 22 mm + MMC5603) was proposed, then **skipped** in favor of going straight to the custom sensor board.

---

## 4. Current firmware – how it works (prototype)

- **Throw pipeline:** 1 s pre-buffer (416 samples) → trigger (accel g **OR** gyro dps over threshold) →
  live release detection (10 samples below free-flight g) → settle 12 + flight 104 samples →
  end on impact (>4 g) / window full / 3 s cap → analyzer → BLE summary. Refractory 1.2 s.
- **Analyzer (`throw_metrics.h`):** finds a still window before the throw (150 ms, <25 dps, 1±0.15 g) to get gravity;
  quaternion integration of the gyro; world-frame velocity → **speed**; **launch, hyzer, nose** from disc
  attitude and velocity at release (hyzer sign flipped for clockwise spin); **wobble**; **spin** from gyro,
  or above 333 rpm from a phase-fit of the drag "wave" and/or centripetal √(a/r) (r learned or calibrated).
- Flags: VALID 1, GYRO_Z_SAT 2, ACCEL_SAT 4, NO_RELEASE 8, NO_STATIC 16, SPIN_FROM_ACC 32, SHORT_FLIGHT 64, SPIN_CCW 128.
- **Sensitivity levels 1–5** (trigG / trigDps / minPeakG / minSpinRpm / freeG / allowNoRelease):
  1: 1.4/120/1.4/0/1.25/yes · 2: 2.0/250/2.0/15/1.6/yes · 3: 2.5/400/2.5/30/2.2/no · 4: 3.0/500/3.0/45/2.6/no · 5: 3.5/600/3.5/60/3.0/no
- **Placement calibration:** disc flat → board-to-disc rotation R (Rodrigues) applied in the driver + gyro bias. Saved to internal flash.
- **Power:** auto-standby after 5 min still (wake-on-motion), auto-off after 4 h, low battery 3.45 V. TX +8 dBm.
- **FIFO lessons:** pattern-register alignment, keep one set in reserve, post-read pattern check, filler samples for lost sets
  (BLE activity caused ~6% loss before the fix).

### BLE protocol (service `19B10000-E8F2-537E-4F6C-D104768A1214`, all packets ≤20 bytes because MTU is 23)
| Char | Use |
|---|---|
| …0001 | throw summary v3 (20 B, byte 19 = spin source) |
| …0002 | commands (text): cal, bias, clear, dump, standby, wake, off, find, findstop, ledon, ledoff, sens N, spincal, streamon, streamoff, logclear, mark N |
| …0003 | raw dump |
| …0004 | live v2 (up-vector, accel, signed spin, rot, throws, alt spin) |
| …0005 | status (20 B: cal, battery, tilt, flags, captures, endReason, flight, rejectFlags, power mode) |
| …0006 | finder RSSI (8 B) |
| …0007 | data-log status (12 B: flags ok/recording/full/stopped-full, records, usedKB, capacityKB, seconds, last test marker) |
| …0008 | data-log download: [u32 offset][bytes]; 0xFFFFFFFF start [total, records, crc32], 0xFFFFFFFE end. Cmd `logread <offset>`. MTU 247 + 8-deep notify queue (configPrphConn(247,12,8,2)) → ~41 KB/s |

### Raw data recorder (new, 2026-10-07/08)
- Every capture (counted **and** rejected) stored on the 2 MB flash with all raw samples + every result + settings.
- **Full sensor recording** button (website, Calibrate & test): every sample at 416 Hz ≈ **5.4 KB/s → ~6.5 min** fills 2 MB;
  **stops automatically when full** until exported. Disc stays awake while recording. LED: blue 1 s = recording, red 2 s = full.
- Test markers (Drop / Net / Real throw / Hand spin / Other) written into the log.
- Export over USB: `py disclab.py export --clear` → CSVs in `analysis\data\<date>` (erases only after a verified export).
  `disclab.py analyze` re-runs a Python port of the analyzer with tunable filters to compare against labels/reference values.

---

## 5. Known problems / findings from testing

- Field testing: **too many non-throws logged**, **speed seems too low**, **spin and simulation off**.
  Of 141 recordings at sensitivity 5, 35 counted; a counted one had hyzer 154° / nose −57° (junk with NO_STATIC + SHORT_FLIGHT).
- Proposed filters (testable offline in disclab, not yet in firmware): reject NO_STATIC, reject SHORT_FLIGHT,
  min spin 150–200 rpm, launch/hyzer sanity limits, an "arm for throw" mode, keep/delete review.
- Root cause for hard throws: gyro saturates at 333 rpm during the pull → 100–160° of missed rotation → wrong
  acceleration direction → speed reads low, angles off. Also ±16 g can clip on hard pulls. → motivates the custom PCB.
- Board-on-XIAO accelerometer is a few mm off-center, so centripetal spin from it is weak/uncertain.

## 6. Practical lessons
- Compile with arduino-cli from a path **without spaces** (OneDrive path breaks the build).
- Flash: 1200-baud touch → bootloader (PID 0045) → `adafruit-nrfutil dfu serial --singlebank`. "Write timeout"/"No data received"
  usually = bad cable or Serial Monitor holding the port. App PID 8045.
- Old firmware put the QSPI flash in deep power-down; send 0xAB before init.
- `File` is ambiguous with SPIFlash + LittleFS → use `Adafruit_LittleFS_Namespace::File`.
- 3D view: USB-C is the "front" of the disc; roll sign convention fixed (right edge down = +).
- Verification gear suggested: laser tachometer + reflective tape, drill press / motor with a centered 3D-printed hub (300–2,500 rpm), radar gun, slow-mo video. Safety guard for 2,500 rpm.

## 7. Open decisions / next steps
1. PCB board shape: round ~48 mm or "+" cross.
2. Buzzer pin (see 3.4 conflict).
3. Add a 16 MB flash (W25Q128) to the board? (Recommended; needs SPI CS → pin pressure again; could share CS lines with a DNP position or use a step-2 board.)
4. KiCad schematic: 5 footprints, 3 populated, buzzer; then Gerbers/BOM/CPL for JLCPCB.
5. Firmware side: in-firmware junk filters, then drivers for the new board.
