# -*- coding: utf-8 -*-
"""
topo_localize — diagnoza topology-aware na NAPRAWIONYM grafie (topo_repaired/).
localize(dark_onts): lista ciemnych ONT -> najniższy wspólny element upstream (LCA)
 + zasięg dotkniętych (ONT/HP/PE poniżej) + coverage_ratio + confidence.
Granice: czysta topologia; ZERO RRD/decyzji. ONT->słupek z ont_to_hp.csv.
"""
import csv, sys, os
from collections import defaultdict, deque
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from . import paths as _cfg
B = _cfg.TOPO_DIR.rstrip("/\\") + "/"

class Topo:
    def __init__(self):
        self.adj=defaultdict(set); self.label={}; self.typ={}
        self.parent={}; self.depth={}; self.root_of={}
        self.label2node={}
        self.ont_by_slupek=defaultdict(list)   # node -> [ont_id]
        self.hp_by_slupek=defaultdict(int)      # node -> liczba HP active
        self.ont_node={}                        # ont_id -> node(słupek)

def load():
    T=Topo()
    for r in csv.DictReader(open(B+"nodes.csv",encoding="utf-8"),delimiter=";"):
        n=(int(r["x_2180"]),int(r["y_2180"])); T.label[n]=r["label"]; T.typ[n]=r["type"]
        if r["label"]: T.label2node[r["label"]]=n
    for r in csv.DictReader(open(B+"edges.csv",encoding="utf-8"),delimiter=";"):
        a=(int(r["ax"]),int(r["ay"])); b=(int(r["bx"]),int(r["by"])); T.adj[a].add(b); T.adj[b].add(a)
    # zakorzenienie multi-source od OLT (WW)
    roots=[n for n,t in T.typ.items() if t=="WW"]; dq=deque()
    for rt in roots: T.parent[rt]=None; T.depth[rt]=0; T.root_of[rt]=rt; dq.append(rt)
    while dq:
        x=dq.popleft()
        for y in T.adj[x]:
            if y not in T.depth:
                T.parent[y]=x; T.depth[y]=T.depth[x]+1; T.root_of[y]=T.root_of[x]; dq.append(y)
    # HP per słupek (active)
    for r in csv.DictReader(open(B+"hp_to_slupek.csv",encoding="utf-8"),delimiter=";"):
        if r["status"]=="active" and r["slupek"] in T.label2node:
            T.hp_by_slupek[T.label2node[r["slupek"]]]+=1
    # ONT per słupek (z ont_to_hp)
    for r in csv.DictReader(open(B+"ont_to_hp.csv",encoding="utf-8"),delimiter=";"):
        sl=r["slupek"]
        if sl in T.label2node:
            oid=f'{r["olt_ont"]}|{r["port_gpon"]}|{r["ont_index"]}'; nd=T.label2node[sl]
            T.ont_by_slupek[nd].append(oid); T.ont_node[oid]=nd
    return T

def _anc(T,n):
    out=[]; x=n
    while x is not None: out.append(x); x=T.parent.get(x)
    return out

def lca(T,nodes):
    nodes=[n for n in nodes if n in T.depth]
    if not nodes: return None
    common=set(_anc(T,nodes[0]))
    for n in nodes[1:]: common &= set(_anc(T,n))
    return max(common,key=lambda x:T.depth.get(x,-1)) if common else None

def subtree(T,root):
    seen={root}; q=deque([root])
    while q:
        x=q.popleft()
        for y in T.adj[x]:
            if T.parent.get(y)==x and y not in seen: seen.add(y); q.append(y)
    return seen

def affected(T,node):
    sub=subtree(T,node)
    onts=[o for nd in sub for o in T.ont_by_slupek.get(nd,[])]
    hp=sum(T.hp_by_slupek.get(nd,0) for nd in sub)
    pe=[T.label[nd] for nd in sub if str(T.label.get(nd,"")).startswith("PE/")]
    return {"ont":onts,"hp":hp,"pe":pe}

def localize(T,dark_onts):
    nodes=[T.ont_node[o] for o in dark_onts if o in T.ont_node]
    unresolved=[o for o in dark_onts if o not in T.ont_node]
    if not nodes:
        return {"resolved":False,"reason":"żaden ONT nie zmapowany do słupka","unresolved":len(unresolved)}
    roots={T.root_of.get(n) for n in nodes}; roots.discard(None)
    anc=lca(T,nodes)
    if anc is None:
        return {"resolved":False,"reason":"brak wspólnego przodka (różne komponenty/korzenie)","roots":[T.label.get(r) for r in roots]}
    aff=affected(T,anc)
    exp=len(aff["ont"]); obs=len(set(nodes))  # ile słupków ciemnych
    dark_below=sum(1 for o in dark_onts if o in T.ont_node and T.ont_node[o] in subtree(T,anc))
    cov=round(dark_below/exp,3) if exp else 0.0
    lvl=T.typ.get(anc);
    conf=round((1.0 if len(roots)==1 else 0.0)*(0.5+0.5*min(cov,1.0)),3)
    return {"resolved":True,
            "common_element":{"type":lvl,"label":T.label.get(anc),"depth":T.depth.get(anc)},
            "root_olt":[T.label.get(r) for r in roots],
            "dark_onts_in":len(dark_onts),"unresolved":len(unresolved),
            "affected_below":{"ont":exp,"hp":aff["hp"],"pe":len(aff["pe"])},
            "dark_observed_below":dark_below,"coverage_ratio":cov,"confidence":conf}

if __name__=="__main__":
    import json
    T=load()
    print(f"== LOAD == węzły={len(T.adj)} | OLT={sum(1 for t in T.typ.values() if t=='WW')} | "
          f"słupki z ONT={len(T.ont_by_slupek)} | ONT zmapowane={len(T.ont_node)}")
    # SELF-TEST: weź słupek z kilkoma ONT, zasymuluj że wszystkie zgasły -> localize ma wskazać ten słupek
    cand=sorted(T.ont_by_slupek.items(), key=lambda kv:-len(kv[1]))
    nd,onts=cand[3]
    print(f"\n== SELF-TEST: padł słupek {T.label[nd]} ({len(onts)} ONT) ==")
    r=localize(T,onts)
    print("  wskazany element:",r["common_element"],"| coverage:",r["coverage_ratio"],"| conf:",r["confidence"])
    print("  dotknięci poniżej:",r["affected_below"])
    # test 2: dwa słupki TEGO SAMEGO OLT -> wspólny element upstream (archetyp mass-outage)
    root0=T.root_of.get(nd)
    nd2,onts2=next(((m,o) for m,o in cand if m!=nd and T.root_of.get(m)==root0), (None,None))
    print(f"\n== TEST 2: ciemne ONT z DWÓCH słupków tego samego OLT ({T.label[nd]} + {T.label.get(nd2)}) ==")
    r2=localize(T,onts[:3]+onts2[:3])
    if r2.get("resolved"):
        print("  wspólny element upstream:",r2["common_element"])
        print("  affected poniżej:",r2["affected_below"],"| coverage:",r2["coverage_ratio"],"| conf:",r2["confidence"])
    else: print("  ",r2)
    # test 3: różne OLT -> ma odmówić (topology-honest)
    nd3,onts3=next(((m,o) for m,o in cand if T.root_of.get(m)!=root0),(None,None))
    print(f"\n== TEST 3: ciemne ONT z RÓŻNYCH OLT (powinno odmówić) ==")
    print("  ",localize(T,onts[:2]+onts3[:2]))
