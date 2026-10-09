#!/bin/sh
# Export fabrication + assembly files for JLCPCB from the routed board.
# usage: sh gen/fab.sh   (run from hardware/kicad)
set -e
PCB=disctracker_sensor.kicad_pcb
SCH=disctracker_sensor.kicad_sch
OUT=fab
rm -rf "$OUT" && mkdir -p "$OUT/gerbers"
kicad-cli pcb drc --schematic-parity --severity-all --exit-code-violations -o "$OUT/drc.rpt" "$PCB"
kicad-cli pcb export gerbers -o "$OUT/gerbers/" \
  --layers F.Cu,In1.Cu,In2.Cu,B.Cu,F.Paste,B.Paste,F.SilkS,B.SilkS,F.Mask,B.Mask,Edge.Cuts \
  --subtract-soldermask --use-drill-file-origin "$PCB"
kicad-cli pcb export drill -o "$OUT/gerbers/" --format excellon --excellon-separate-th \
  --generate-map --map-format gerberx2 "$PCB"
( cd "$OUT/gerbers" && zip -q ../disctracker_sensor_gerbers.zip * )
# Pick-and-place for the machine-assembled sensor face only (DNP parts excluded)
kicad-cli pcb export pos -o "$OUT/pos_front.csv" --side front --format csv --units mm \
  --exclude-dnp --smd-only "$PCB"
kicad-cli sch export bom -o "$OUT/bom_all.csv" \
  --fields 'Reference,Value,Footprint,${DNP},MPN,LCSC,Description' \
  --group-by 'Value,Footprint,${DNP}' "$SCH"
kicad-cli pcb export step -o "$OUT/disctracker_sensor.step" --subst-models --force "$PCB"
kicad-cli sch export pdf -o "$OUT/schematic.pdf" "$SCH"
kicad-cli pcb render --side top -w 1600 -h 1600 -o "$OUT/render_sensor_face.png" "$PCB"
kicad-cli pcb render --side bottom -w 1600 -h 1600 -o "$OUT/render_xiao_face.png" "$PCB"
echo done
