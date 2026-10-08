# Battery options (pick one)

Constraints: protected LiPo, >= 50 mAh (XIAO charges at 50 mA), <= ~4 mm thick (XIAO is ~4.0 mm tall, measured),
fits the -X half of the 56 mm board, and balances the XIAO (2.027 g measured, centered at +15 mm = 30.4 g*mm).
"Balance position" = where the battery's center must sit (-X) so it cancels the XIAO with no extra weight.
Leftover = imbalance a solder trim pad must make up (1 g*mm ~ 0.04 g of solder at 25 mm).

| # | Cell | mAh | T x W x L mm | g | Balance position | Fits balanced? | Where |
|---|---|---|---|---|---|---|---|
| A | EEMB LP301730 | 100 | 3.3 x 17.5 x 31 | 2.0 | -15.2 | almost (2.5 g*mm trim) | EEMB / distributors |
| B | EEMB LP401730 | 150 | 4.3 x 17.5 x 31 | 2.8 | -10.9 | yes (pod +0.3 mm taller) | EEMB / distributors |
| C | Adafruit 1570 | 100 | 3.8 x 11.5 x 31 | 3.0 | -10.1 | yes | adafruit.com/product/1570 |
| D | Generic 302020 | 110 | ~3.5 x 20 x 22 | ~3 | -10.1 | yes | Amazon B09WN4H4C4 |
| E | Akyga LP401520 | 70 | 4.0 x 15 x 20.5 | ~2 bare (3.3 with lead+plug) | -15.2 | yes | electrokit.com |
| F | EEMB LP302024 | 85 | 3.5 x 20.5 x 25 | 1.7 | -17.9 | no (6.2 g*mm trim) | EEMB / distributors |
| G | EEMB LP301230 | 70 | 3.5 x 12.5 x 31 | 1.4 | -21.7 | no (7.4 g*mm trim) | EEMB / distributors |
| H | Adafruit 1317 | 150 | 3.8 x 19.75 x 26 | 4.65 | -6.5 | yes, but heavy | adafruit.com/product/1317 |
| I | YDL 401520 | 80 | 4.0 x 15 x 20 | 4 (listed) | -7.6 | yes, heavy | ydlbattery.com |

Notes: listed weights vary by seller and include leads/plugs; cut leads short and solder to J1/J2.
EEMB specs from the EEMB Li-polymer overview table. Runtime estimate ~8 mA active -> 70 mAh ~ 8 h, 100 mAh ~ 12 h.
Final balance: weigh-and-trim the assembled pod on a center pin; trim pads on +/-X and +/-Y.

## Runtime estimate (new board, 3 IMUs fitted; 80% of capacity usable)
Current budget (estimate): 3x LSM6DSV320X 2.7 mA (datasheet ~0.9 mA each) + MMC5603 at 100 Hz 1.3 mA (datasheet)
+ nRF52840 reading 1,920 Hz + processing ~3 mA + Bluetooth ~1 mA = ~8 mA active (6-12 mA range).

| Mode | 70 mAh | 85 | 100 | 110 | 150 |
|---|---|---|---|---|---|
| Active, ~8 mA | 7 h | 8.5 h | 10 h | 11 h | 15 h |
| Active, worst case 12 mA | 4.7 h | 5.7 h | 6.7 h | 7.3 h | 10 h |
| Standby (wake on motion), ~0.1 mA | 23 days | 28 days | 33 days | 37 days | 50 days |
| Off, ~15 uA | months (self-discharge limits) | | | | |
| Charge time at 50 mA (100 mA) | 1.6 h (0.8) | 2.0 (1.0) | 2.3 (1.2) | 2.5 (1.3) | 3.4 (1.8) |

Magnetometer at 1 kHz would add ~10+ mA: run it at 100 Hz and only go to 1 kHz around a throw.
Verify by measuring the current prototype with a USB power meter or Nordic PPK2.
