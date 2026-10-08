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
