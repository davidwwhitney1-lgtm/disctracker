#!/usr/bin/env python3
"""Bundle the meshes the viewer needs into models.json (base64 STL) for publishing the page as one artifact.
usage: python bundle.py ../out models.json"""
import base64, json, sys
NAMES = ["ref_disc", "dock", "pod", "cover", "ref_board", "ref_parts", "ref_xiao", "ref_battery", "jig_frame", "jig_plunger"]
src, dst = sys.argv[1], sys.argv[2]
json.dump({n: base64.b64encode(open(f"{src}/{n}.stl", "rb").read()).decode() for n in NAMES}, open(dst, "w"))
