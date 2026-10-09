#!/usr/bin/env python3
"""Generate the DiscTracker sensor-board KiCad 9 project (symbol lib + schematic)."""
import os, re, sys, uuid, shutil
from sx import get_symbol, pins

OUT = sys.argv[1]
SEEED_FP = sys.argv[2]
KLIB = "/usr/share/kicad/symbols/"
NS = uuid.UUID("6f1c2a52-8d0e-4c51-9a77-1d1d5c0e0d15")
def uid(*k): return str(uuid.uuid5(NS, "/".join(map(str, k))))
ROOT = uid("root")
PROJECT = "disctracker_sensor"

def F(v):  # format a number on KiCad's grid
    v = round(v, 4)
    return ("%.4f" % v).rstrip("0").rstrip(".") if v != int(v) else str(int(v))

def eff(size=1.27, hide=False, justify=None, bold=False):
    j = f" (justify {justify})" if justify else ""
    b = " (bold yes)" if bold else ""
    h = " (hide yes)" if hide else ""
    return f"(effects (font (size {F(size)} {F(size)}){b}){j}{h})"

# ---------------------------------------------------------------- custom symbols
def pin(t, x, y, a, name, num, length=2.54, hide=False):
    h = " (hide yes)" if hide else ""
    return (f'(pin {t} line (at {F(x)} {F(y)} {a}) (length {F(length)}){h} '
            f'(name "{name}" {eff()}) (number "{num}" {eff()}))')

def sym(name, ref, value, fp, ds, desc, body, pinlist, refat, valat, extra=None, kw=""):
    props = [
        f'(property "Reference" "{ref}" (at {refat}) {eff(justify="left")})',
        f'(property "Value" "{value}" (at {valat}) {eff(justify="left")})',
        f'(property "Footprint" "{fp}" (at 0 0 0) {eff(hide=True)})',
        f'(property "Datasheet" "{ds}" (at 0 0 0) {eff(hide=True)})',
        f'(property "Description" "{desc}" (at 0 0 0) {eff(hide=True)})',
    ]
    for k, v in (extra or {}).items():
        props.append(f'(property "{k}" "{v}" (at 0 0 0) {eff(hide=True)})')
    if kw:
        props.append(f'(property "ki_keywords" "{kw}" (at 0 0 0) {eff(hide=True)})')
    return (f'(symbol "{name}" (exclude_from_sim no) (in_bom yes) (on_board yes)\n  '
            + "\n  ".join(props)
            + f'\n  (symbol "{name}_0_1" {body})\n  (symbol "{name}_1_1"\n    '
            + "\n    ".join(pinlist) + "))")

RECT = lambda x1, y1, x2, y2: (f"(rectangle (start {F(x1)} {F(y1)}) (end {F(x2)} {F(y2)}) "
                              f"(stroke (width 0.254) (type default)) (fill (type background)))")

LSM_PINS = [
    pin("input", -15.24, 7.62, 0, "SCL/SPC", "13"),
    pin("bidirectional", -15.24, 5.08, 0, "SDA/SDI", "14"),
    pin("tri_state", -15.24, 2.54, 0, "SDO/TA0", "1"),
    pin("input", -15.24, 0, 0, "~{CS}", "12"),
    pin("passive", -15.24, -5.08, 0, "SDx", "2"),
    pin("passive", -15.24, -7.62, 0, "SCx", "3"),
    pin("output", 15.24, 5.08, 180, "INT1", "4"),
    pin("output", 15.24, 2.54, 180, "INT2", "9"),
    pin("input", 15.24, -2.54, 180, "OCS_Aux", "10"),
    pin("output", 15.24, -5.08, 180, "SDO_Aux", "11"),
    pin("power_in", -2.54, 12.7, 270, "VDD", "8"),
    pin("power_in", 2.54, 12.7, 270, "VDDIO", "5"),
    pin("power_in", -2.54, -15.24, 90, "GND", "6"),
    pin("power_in", 2.54, -15.24, 90, "GND", "7"),
]
LSM = sym("LSM6DSV320X", "U", "LSM6DSV320X",
          "Package_LGA:LGA-14_3x2.5mm_P0.5mm_LayoutBorder3x4y",
          "https://www.st.com/resource/en/datasheet/lsm6dsv320x.pdf",
          "6-axis IMU, gyro +/-4000 dps, accel +/-16 g plus high-g +/-32..320 g, SPI/I2C/I3C, LGA-14 2.5x3.0x0.83 mm",
          RECT(-12.7, 10.16, 12.7, -12.7), LSM_PINS, "5.08 13.97 0", "5.08 -13.97 0",
          {"MPN": "LSM6DSV320XTR"}, "IMU accelerometer gyroscope high-g ST")

XIAO_PINS = [
    pin("bidirectional", -21.59, 19.05, 0, "D0", "1"),
    pin("bidirectional", -21.59, 15.24, 0, "D1", "2"),
    pin("bidirectional", -21.59, 11.43, 0, "D2", "3"),
    pin("bidirectional", -21.59, 7.62, 0, "D3", "4"),
    pin("bidirectional", -21.59, 3.81, 0, "D4/SDA", "5"),
    pin("bidirectional", -21.59, 0, 0, "D5/SCL", "6"),
    pin("bidirectional", -21.59, -3.81, 0, "D6/TX", "7"),
    pin("bidirectional", 16.51, -3.81, 180, "D7/RX", "8"),
    pin("bidirectional", 16.51, 0, 180, "D8/SCK", "9"),
    pin("bidirectional", 16.51, 3.81, 180, "D9/MISO", "10"),
    pin("bidirectional", 16.51, 7.62, 180, "D10/MOSI", "11"),
    pin("power_out", 16.51, 11.43, 180, "3V3", "12"),
    pin("power_in", 16.51, 15.24, 180, "GND", "13"),
    pin("passive", 16.51, 19.05, 180, "VBUS", "14"),
    pin("bidirectional", -7.62, 26.67, 270, "SWDIO", "15"),
    pin("input", -3.81, 26.67, 270, "SWCLK", "16"),
    pin("passive", 0, 26.67, 270, "EN", "17"),
    pin("power_in", 3.81, 26.67, 270, "GND", "18"),
    pin("passive", -7.62, -10.16, 90, "VBAT", "19"),
    pin("power_in", -3.81, -10.16, 90, "GND", "20"),
    pin("passive", 0, -10.16, 90, "NFC1", "21"),
    pin("passive", 3.81, -10.16, 90, "NFC2", "22"),
]
XIAO = sym("XIAO_nRF52840_Sense_SMD", "M", "XIAO nRF52840 Sense",
           "disctracker:XIAO-nRF52840-SMD", "https://wiki.seeedstudio.com/XIAO_BLE/",
           "Seeed Studio XIAO nRF52840 (Sense), surface-mount on castellated + underside pads",
           RECT(-19.05, 24.13, 13.97, -7.62), XIAO_PINS, "-19.05 29.21 0", "-19.05 -14.605 0",
           {"MPN": "102010469"}, "nRF52840 BLE XIAO Seeed")

# MMC5603NJ: KiCad's MMC5633NJL has the identical 4-ball pinout; rename it.
mmc = get_symbol(KLIB + "Sensor_Magnetic.kicad_sym", "MMC5633NJL").replace("MMC5633NJL", "MMC5603NJ")
mmc = re.sub(r'\(property "Datasheet" "[^"]*"', '(property "Datasheet" "https://www.espruino.com/files/MMC5603NJ.pdf"', mmc)
mmc = re.sub(r'\(property "Description" "[^"]*"', '(property "Description" "3-axis AMR magnetometer, +/-30 G, I2C 0x30, up to 1 kHz, WLCSP-4 0.8x0.8 mm"', mmc)

CUSTOM = {"LSM6DSV320X": LSM, "XIAO_nRF52840_Sense_SMD": XIAO, "MMC5603NJ": mmc}

os.makedirs(OUT, exist_ok=True)
with open(f"{OUT}/disctracker.kicad_sym", "w") as f:
    f.write('(kicad_symbol_lib (version 20241209) (generator "disctracker_gen") (generator_version "9.0")\n')
    for s in CUSTOM.values():
        f.write("  " + s + "\n")
    f.write(")\n")

# footprints: copy the Seeed XIAO SMD footprint (CC BY-SA 4.0) into the project library
os.makedirs(f"{OUT}/disctracker.pretty", exist_ok=True)
shutil.copy(SEEED_FP, f"{OUT}/disctracker.pretty/XIAO-nRF52840-SMD.kicad_mod")

# ---------------------------------------------------------------- library cache
def lib_block(lib_id):
    lib, name = lib_id.split(":")
    if lib == "disctracker":
        b = CUSTOM[name]
    else:
        b = get_symbol(KLIB + lib + ".kicad_sym", name)
    return b.replace(f'(symbol "{name}"', f'(symbol "{lib_id}"', 1), pins(b)

USED = {}
def libsym(lib_id):
    if lib_id not in USED:
        USED[lib_id] = lib_block(lib_id)
    return USED[lib_id][1]

# ---------------------------------------------------------------- schematic items
items = []
def wire(x1, y1, x2, y2):
    items.append(f'(wire (pts (xy {F(x1)} {F(y1)}) (xy {F(x2)} {F(y2)})) (stroke (width 0) (type default)) (uuid "{uid("w", x1, y1, x2, y2)}"))')
def label(net, x, y, ang):
    just = {0: "left bottom", 180: "right bottom", 90: "left bottom", 270: "right bottom"}[ang]
    items.append(f'(label "{net}" (at {F(x)} {F(y)} {ang}) (fields_autoplaced yes) {eff(justify=just)} (uuid "{uid("l", net, x, y)}"))')
def noconn(x, y):
    items.append(f'(no_connect (at {F(x)} {F(y)}) (uuid "{uid("nc", x, y)}"))')
def text(t, x, y, size=1.27, bold=False):
    t = t.replace('"', "'").replace("\n", "\\n")
    items.append(f'(text "{t}" (exclude_from_sim no) (at {F(x)} {F(y)} 0) {eff(size, justify="left top", bold=bold)} (uuid "{uid("t", x, y)}"))')
def box(x1, y1, x2, y2, title):
    items.append(f'(rectangle (start {F(x1)} {F(y1)}) (end {F(x2)} {F(y2)}) (stroke (width 0.15) (type dash)) (fill (type none)) (uuid "{uid("r", x1, y1)}"))')
    text(title, x1 + 1.27, y1 + 1.27, 2, True)

STUB = 2.54
NETS = {}  # net -> list of (ref, pin)
def place(lib_id, ref, value, x, y, conn, fp="", ds="", dnp=False, fields=None,
          refoff=None, valoff=None, on_board=True, in_bom=True, desc=""):
    """conn: pin number -> net name, or None for no-connect."""
    plist = libsym(lib_id)
    rx, ry = refoff if refoff else (3.81, -1.27)
    vx, vy = valoff if valoff else (3.81, 1.27)
    props = [
        f'(property "Reference" "{ref}" (at {F(x+rx)} {F(y+ry)} 0) {eff(justify="left", hide=ref.startswith("#"))})',
        f'(property "Value" "{value}" (at {F(x+vx)} {F(y+vy)} 0) {eff(justify="left")})',
        f'(property "Footprint" "{fp}" (at {F(x)} {F(y)} 0) {eff(hide=True)})',
        f'(property "Datasheet" "{ds}" (at {F(x)} {F(y)} 0) {eff(hide=True)})',
        f'(property "Description" "{desc}" (at {F(x)} {F(y)} 0) {eff(hide=True)})',
    ]
    for k, v in (fields or {}).items():
        props.append(f'(property "{k}" "{v}" (at {F(x)} {F(y)} 0) {eff(hide=True)})')
    pins_s = " ".join(f'(pin "{p["num"]}" (uuid "{uid(ref, "pin", p["num"])}"))' for p in plist)
    items.append(
        f'(symbol (lib_id "{lib_id}") (at {F(x)} {F(y)} 0) (unit 1) (exclude_from_sim no) '
        f'(in_bom {"yes" if in_bom else "no"}) (on_board {"yes" if on_board else "no"}) (dnp {"yes" if dnp else "no"}) '
        f'(uuid "{uid("sym", ref)}")\n  ' + "\n  ".join(props) + f"\n  {pins_s}\n  "
        f'(instances (project "{PROJECT}" (path "/{ROOT}" (reference "{ref}") (unit 1)))))')
    for p in plist:
        num = p["num"]
        if num not in conn:
            raise SystemExit(f"{ref} pin {num} ({p['name']}) not assigned")
        px, py = x + p["x"], y - p["y"]          # symbol y is up, sheet y is down
        net = conn[num]
        if net is None:
            noconn(px, py); continue
        d = {0: (-1, 0), 180: (1, 0), 90: (0, 1), 270: (0, -1)}[p["a"]]
        ex, ey = px + d[0] * STUB, py + d[1] * STUB
        wire(px, py, ex, ey)
        ang = {(-1, 0): 180, (1, 0): 0, (0, 1): 270, (0, -1): 90}[d]
        label(net, ex, ey, ang)
        NETS.setdefault(net, []).append((ref, num))

R0402, C0402, C0603 = "Resistor_SMD:R_0402_1005Metric", "Capacitor_SMD:C_0402_1005Metric", "Capacitor_SMD:C_0603_1608Metric"
LSM_DS = "https://www.st.com/resource/en/datasheet/lsm6dsv320x.pdf"

# ---------------------------------------------------------------- MCU block
box(12.7, 20.32, 107.95, 109.22, "MCU + radio · XIAO nRF52840 Sense")
place("disctracker:XIAO_nRF52840_Sense_SMD", "M1", "XIAO nRF52840 Sense", 55.88, 60.96, {
    "1": "CS1", "2": "CS2", "3": "CS3", "4": "CS4", "5": "I2C_SDA", "6": "I2C_SCL", "7": "D6_CS5_BZ",
    "8": "IMU_INT1", "9": "SCK_MCU", "10": "SPI_MISO", "11": "SPI_MOSI", "12": "+3V3", "13": "GND",
    "14": None, "15": None, "16": None, "17": None, "18": None, "19": "VBAT", "20": "GND", "21": None, "22": None},
    fp="disctracker:XIAO-nRF52840-SMD", ds="https://wiki.seeedstudio.com/XIAO_BLE/",
    refoff=(7.62, -31.75), valoff=(7.62, -29.21),
    fields={"MPN": "Seeed 102010469", "Placement": "XIAO face, center (+15, 0) mm, USB-C at pod edge"})
place("Device:R", "R3", "33", 93.98, 60.96, {"1": "SCK_MCU", "2": "SPI_SCK"}, fp=R0402,
      desc="Series resistor on SPI clock (20 mm runs)")
place("Device:C", "C12", "10u", 99.06, 88.9, {"1": "+3V3", "2": "GND"}, fp=C0603, desc="Bulk at XIAO 3V3")
text("D0-D10 all used. D6 goes to JP1 (U5 chip-select or buzzer).\nVBUS, SWD, EN, NFC and underside GND pad 18 left unconnected\n(GND via pads 13 and 20; 19/20 are plated holes).\nFirmware: P1.11 (D6) high drive for the buzzer;\ncharge current 100 mA (P0.13 low).", 15.24, 92.71)

# ---------------------------------------------------------------- IMU block
box(114.3, 20.32, 406.4, 160.02, "Motion sensors · 5x LSM6DSV320X on shared SPI (sensor face, all same orientation)")
IMUS = [("U1", "CS1", "IMU_INT1", False, "Center (0, 0)"),
        ("U2", "CS2", None, False, "Pair A +X (+20.00, 0)"),
        ("U3", "CS3", None, False, "Pair A -X (-20.00, 0)"),
        ("U4", "CS4", None, True, "Pair B +Y (0, +20.00) - not fitted"),
        ("U5", "CS5", None, True, "Pair B -Y (0, -20.00) - not fitted")]
cref, rref = 1, 4
for i, (ref, cs, intn, dnp, where) in enumerate(IMUS):
    x = 139.7 + i * 58.42
    place("disctracker:LSM6DSV320X", ref, "LSM6DSV320X", x, 63.5, {
        "13": "SPI_SCK", "14": "SPI_MOSI", "1": "SPI_MISO", "12": cs, "2": "GND", "3": "GND",
        "4": intn, "9": None, "10": None, "11": None, "8": "+3V3", "5": "+3V3", "6": "GND", "7": "GND"},
        fp="Package_LGA:LGA-14_3x2.5mm_P0.5mm_LayoutBorder3x4y", ds=LSM_DS, dnp=dnp,
        refoff=(5.08, -13.97), valoff=(5.08, 13.97),
        fields={"MPN": "LSM6DSV320XTR", "Placement": where})
    text(where, x - 12.7, 86.36)
    for k, what in ((0, "VDD (pin 8)"), (1, "VDDIO (pin 5)")):
        place("Device:C", f"C{cref}", "100n", x - 12.7 + k * 13.97, 106.68, {"1": "+3V3", "2": "GND"},
              fp=C0402, dnp=dnp, desc=f"{ref} {what} decoupling, place next to the pin")
        cref += 1
    place("Device:R", f"R{rref}", "100k", x + 15.24, 106.68, {"1": "+3V3", "2": cs}, fp=R0402, dnp=dnp,
          desc=f"{cs} pull-up (firmware sets I2C_I3C_disable, which turns off the chip's own CS pull-up)")
    rref += 1
text("Pins: 1 SDO -> MISO · 2 SDx, 3 SCx -> GND · 4 INT1 -> D7 (U1 only) · 5 VDDIO, 8 VDD -> 3V3 + 100 nF each · 6, 7 GND\n"
     "9 INT2, 10 OCS_Aux, 11 SDO_Aux: soldered, not connected (datasheet DS14623 Table 2) · 12 CS · 13 SCL/SPC -> SCK · 14 SDA/SDI -> MOSI\n"
     "Firmware: first SPI write to every chip sets I2C_I3C_disable (IF_CFG 03h). High-g +/-256 g at 1.92 kHz; gyro +/-4000 dps.\n"
     "U4, U5, C7-C10, R7, R8 are DNP (pair B, fitted later).", 116.84, 124.46)

# ---------------------------------------------------------------- magnetometer
box(12.7, 165.1, 107.95, 238.76, "Magnetometer · MMC5603NJ (sensor face, (0, -24) mm)")
place("disctracker:MMC5603NJ", "U6", "MMC5603NJ", 48.26, 199.39,
      {"A2": "I2C_SCL", "B2": "I2C_SDA", "B1": "+3V3", "A1": "GND"},
      fp="Package_BGA:WLP-4_0.86x0.86mm_P0.4mm", ds="https://www.espruino.com/files/MMC5603NJ.pdf",
      refoff=(8.89, -1.27), valoff=(8.89, 1.27), fields={"MPN": "MMC5603NJ", "LCSC": "C404328"})
place("Device:C", "C11", "2.2u", 71.12, 199.39, {"1": "+3V3", "2": "GND"}, fp=C0402,
      desc="MMC5603NJ VDD bypass, datasheet minimum 2.2 uF, close to B1")
place("Device:R", "R1", "4.7k", 81.28, 199.39, {"1": "+3V3", "2": "I2C_SDA"}, fp=R0402, desc="I2C SDA pull-up")
place("Device:R", "R2", "4.7k", 93.98, 199.39, {"1": "+3V3", "2": "I2C_SCL"}, fp=R0402, desc="I2C SCL pull-up")
text("I2C address 0x30. Keep >= 10 mm from XIAO, battery and any current-carrying\ntrace on either face. Footprint: verify ball pitch vs MEMSIC drawing.", 15.24, 222.25)

# ---------------------------------------------------------------- buzzer
box(114.3, 165.1, 220.98, 238.76, "Finder buzzer · CUI CPT-9019S on D6 via JP1")
place("Jumper:SolderJumper_3_Open", "JP1", "D6 select", 142.24, 190.5,
      {"1": "CS5", "2": "D6_CS5_BZ", "3": "BZ_DRV"},
      fp="Jumper:SolderJumper-3_P1.3mm_Open_RoundedPad1.0x1.5mm", refoff=(-5.08, -8.89), valoff=(-5.08, -6.35),
      desc="1-2 (A): D6 = U5 chip-select. 2-3 (B): D6 = buzzer. Ship bridged 2-3.")
place("Device:R", "R9", "100", 170.18, 200.66, {"1": "BZ_DRV", "2": "BZ_P"}, fp=R0402,
      desc="Limits GPIO peak current into the piezo's capacitance")
place("Device:Buzzer", "BZ1", "CPT-9019S-SMT", 190.5, 200.66, {"1": "BZ_P", "2": "GND"},
      fp="Buzzer_Beeper:Buzzer_CUI_CPT-9019S-SMT", ds="https://www.sameskydevices.com/product/resource/cpt-9019s-smt.pdf",
      refoff=(-7.62, -6.35), valoff=(-7.62, 6.35), fields={"MPN": "CPT-9019S-SMT-TR", "LCSC": "C95163"},
      desc="Piezo, externally driven, 3 V / 5 mA / 65 dB @ 10 cm, 4 kHz. Non-magnetic.")
text("Ship JP1 bridged 2-3 (buzzer) while U5 is not fitted.\nDrive D6 with a 4 kHz PWM square wave.", 116.84, 222.25)

# ---------------------------------------------------------------- power
box(226.06, 165.1, 312.42, 238.76, "Power · Adafruit 1317 LiPo, 150 mAh")
place("Device:Battery_Cell", "BT1", "Adafruit 1317 150mAh", 241.3, 198.12, {"1": "VBAT", "2": "GND"},
      on_board=False, ds="https://www.adafruit.com/product/1317", refoff=(3.81, -3.81), valoff=(3.81, -1.905),
      fields={"MPN": "Adafruit 1317"}, desc="3.7 V protected LiPo, 19.75 x 26.02 x 3.8 mm, 4.65 g. Leads soldered to J1/J2.")
place("Connector_Generic:Conn_01x01", "J1", "BAT+", 274.32, 190.5, {"1": "VBAT"},
      fp="Connector_Wire:SolderWirePad_1x01_SMD_1.5x3mm", refoff=(2.54, -2.54), valoff=(2.54, 2.54))
place("Connector_Generic:Conn_01x01", "J2", "BAT-", 274.32, 205.74, {"1": "GND"},
      fp="Connector_Wire:SolderWirePad_1x01_SMD_1.5x3mm", refoff=(2.54, -2.54), valoff=(2.54, 2.54))
place("power:PWR_FLAG", "#FLG01", "PWR_FLAG", 294.64, 190.5, {"1": "GND"}, refoff=(0, -6.35), valoff=(0, -4.445))
text("J1/J2 at (-18.4, +/-3) mm on the XIAO face, routed to\nXIAO VBAT (pad 19) / GND (pad 20). Battery bonded,\ncentered at (-6.54, 0) mm to balance the XIAO.", 228.6, 222.25)

# ---------------------------------------------------------------- mechanical
box(317.5, 165.1, 406.4, 238.76, "Mechanical · trim pads and alignment holes")
for i, (ref, where) in enumerate((("TP1", "NE"), ("TP2", "NW"), ("TP3", "SW"), ("TP4", "SE"))):
    place("Connector:TestPoint", ref, f"trim {where}", 330.2 + i * 17.78, 190.5, {"1": None},
          fp="TestPoint:TestPoint_Pad_3.0x3.0mm", refoff=(2.54, -6.35), valoff=(2.54, -4.445),
          desc="Balance trim pad: add solder after weighing the built pod", in_bom=False)
for i in range(3):
    place("Mechanical:MountingHole", f"H{i+1}", "align", 335.28 + i * 22.86, 210.82, {},
          fp="MountingHole:MountingHole_2.1mm", refoff=(2.54, -1.27), valoff=(2.54, 1.27), in_bom=False,
          desc="Pod alignment pin hole, r = 25.6 mm at 30 / 150 / 250 deg")
text("Trim pads at r = 22 mm on the diagonals (XIAO face); SW/SE sit opposite the buzzer.\nHoles locate the board on the pod's pins.", 320.04, 222.25)

# ---------------------------------------------------------------- notes block
box(12.7, 243.84, 226.06, 284.48, "Board notes")
text("56 mm round, 4 layers, 0.8 mm (0.6 mm or cutouts to save weight). Solid GND plane under the sensors.\n"
     "Sensor face (machine assembled): U1-U6, C1-C11, R1-R9, JP1 · XIAO face (hand-soldered): M1, BZ1, C12, J1/J2, TP1-TP4, battery.\n"
     "U1 exactly at board center; U2/U3 centers at (+/-20.00, 0); U4/U5 at (0, +/-20.00). Measure to package center.\n"
     "Every off-center mass mirrored or trimmed. Magnetometer clear of XIAO, battery, buzzer and current traces.\n"
     "Source of truth for positions: hardware/placement.csv · pins: hardware/pinmap.csv · overview: hardware/overview.html", 15.24, 250.19)

# ---------------------------------------------------------------- write schematic
lib_s = "\n    ".join(b for b, _ in USED.values())
sch = f'''(kicad_sch (version 20250114) (generator "eeschema") (generator_version "9.0")
  (uuid "{ROOT}")
  (paper "A3")
  (title_block (title "DiscTracker sensor board") (date "2026-10-08") (rev "0.1")
    (company "Messiah University · David Whitney")
    (comment 1 "Step 1: sensor board with XIAO nRF52840 Sense soldered on")
    (comment 2 "56 mm round · spin pair r = 20.00 mm · build: U1 + U2 + U3")
    (comment 3 "Generated from hardware/kicad/gen - edit freely in KiCad 9"))
  (lib_symbols
    {lib_s})
  {chr(10).join("  " + it for it in items)}
  (sheet_instances (path "/" (page "1")))
  (embedded_fonts no))
'''
open(f"{OUT}/{PROJECT}.kicad_sch", "w").write(sch)

# project file + library tables
open(f"{OUT}/{PROJECT}.kicad_pro", "w").write('''{
  "meta": { "filename": "%s.kicad_pro", "version": 3 },
  "schematic": { "legacy_lib_dir": "", "legacy_lib_list": [] },
  "sheets": [ [ "%s", "Root" ] ],
  "boards": [],
  "libraries": { "pinned_footprint_libs": [], "pinned_symbol_libs": [] }
}
''' % (PROJECT, ROOT))
open(f"{OUT}/sym-lib-table", "w").write('(sym_lib_table (version 7)\n  (lib (name "disctracker")(type "KiCad")(uri "${KIPRJMOD}/disctracker.kicad_sym")(options "")(descr "DiscTracker custom symbols"))\n)\n')
open(f"{OUT}/fp-lib-table", "w").write('(fp_lib_table (version 7)\n  (lib (name "disctracker")(type "KiCad")(uri "${KIPRJMOD}/disctracker.pretty")(options "")(descr "DiscTracker footprints (XIAO from Seeed OPL, CC BY-SA 4.0)"))\n)\n')


print("ok", len(items), "items;", len(NETS), "nets")
