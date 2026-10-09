#!/usr/bin/env python3
"""Report GND copper (pour islands, pads) with no path to the In1 GND plane. usage: check_gnd.py <board>"""
import sys, pcbnew
from pcbnew import ToMM, VECTOR2I
b=pcbnew.LoadBoard(sys.argv[1])
g=b.FindNet("/GND").GetNetCode()
par={}
def f(x):
    par.setdefault(x,x)
    while par[x]!=x: par[x]=par[par[x]]; x=par[x]
    return x
def u(a,c): par[f(a)]=f(c)
ROOT="IN1"
isl=[]  # (key, layer, polyset, idx)
for z in b.Zones():
    if z.GetIsRuleArea() or z.GetNetCode()!=g: continue
    for L in (pcbnew.F_Cu,pcbnew.B_Cu,pcbnew.In1_Cu):
        if not z.IsOnLayer(L): continue
        ps=z.GetFilledPolysList(L)
        for i in range(ps.OutlineCount()):
            k=("Z",L,i); isl.append((k,L,ps,i))
            if L==pcbnew.In1_Cu: u(k,ROOT)
def touch(pos,L):
    return [k for k,LL,ps,i in isl if LL==L and ps.Contains(pos,i)]
tr=[t for t in b.GetTracks() if t.GetNetCode()==g]
for t in tr:
    k=("T",str(t.m_Uuid.AsString()))
    if t.GetClass()=="PCB_VIA":
        u(k,ROOT)
        for L in (pcbnew.F_Cu,pcbnew.B_Cu):
            for z in touch(t.GetPosition(),L): u(k,z)
    else:
        for p in (t.GetStart(),t.GetEnd()):
            for z in touch(p,t.GetLayer()): u(k,z)
# tracks touching each other / pads at endpoints
pads=[(fp.GetReference(),p) for fp in b.GetFootprints() for p in fp.Pads() if p.GetNetCode()==g]
for ref,p in pads:
    k=("P",ref+":"+p.GetNumber())
    if p.GetAttribute()==pcbnew.PAD_ATTRIB_PTH: u(k,ROOT)
    for L in (pcbnew.F_Cu,pcbnew.B_Cu):
        if p.IsOnLayer(L):
            for z in touch(p.GetPosition(),L): u(k,z)
    for t in tr:
        if t.GetClass()=="PCB_VIA":
            if p.HitTest(t.GetPosition()): u(k,("T",str(t.m_Uuid.AsString())))
        else:
            for q in (t.GetStart(),t.GetEnd()):
                if p.HitTest(q) and p.IsOnLayer(t.GetLayer()): u(k,("T",str(t.m_Uuid.AsString())))
for t in tr:
    for s in tr:
        if t is s or t.GetClass()=="PCB_VIA" and s.GetClass()=="PCB_VIA": continue
        pts_t=[t.GetPosition()] if t.GetClass()=="PCB_VIA" else [t.GetStart(),t.GetEnd()]
        pts_s=[s.GetPosition()] if s.GetClass()=="PCB_VIA" else [s.GetStart(),s.GetEnd()]
        if any(a.x==c.x and a.y==c.y for a in pts_t for c in pts_s):
            u(("T",str(t.m_Uuid.AsString())),("T",str(s.m_Uuid.AsString())))
for k,L,ps,i in isl:
    if f(k)!=f(ROOT):
        bb=ps.Outline(i).BBox()
        print("FLOATING", b.GetLayerName(L), round(ToMM(bb.GetX()),2), round(ToMM(bb.GetY()),2), round(ToMM(bb.GetWidth()),2), round(ToMM(bb.GetHeight()),2))
for ref,p in pads:
    k=("P",ref+":"+p.GetNumber())
    if f(k)!=f(ROOT): print("FLOATING PAD", k[1])
