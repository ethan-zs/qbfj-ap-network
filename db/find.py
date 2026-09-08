#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
贴新闻 / 合回之前先查人、查机构，省得手算 id。

用法：
  python3 find.py 卢策吾 王鹤              # 按姓名查（可多个，四校都查）：DB0 行、页面 _id、db 文档 id、快照里的覆盖记录
  python3 find.py --sch t 刘洋             # 限定学校 s/f/t/p（同名多校时用）
  python3 find.py --inv 顺为资本 高瓴       # 投资机构：DB0 里投过谁、是否在 CORP/STATE/SCHOOL_FUND/IALIAS 登记

快照 db/profs.json 可能不是最新的，写 db 之前以 Artifact read_db 为准。
"""
import io,json,os,re,sys
HERE=os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0,HERE)
from merge_news import load_db0,assign_ids,hid,HTML
SCH={"s":"交大","f":"复旦","t":"清华","p":"北大"}

def snapshot():
    try: s=json.load(io.open(os.path.join(HERE,"profs.json"),encoding="utf-8"))
    except Exception: return [],None
    docs=s.get("docs",[]) if isinstance(s,dict) else s
    return [(x.get("id"),x.get("data",x)) for x in docs],(s.get("snapshotAt") if isinstance(s,dict) else None)

def registry():
    h=io.open(HTML,encoding="utf-8").read()
    grab=lambda pat:(re.search(pat,h,re.S) or [None,""])[1]
    corp=set(json.loads("["+grab(r"const CORP=new Set\(\[(.*?)\]\);")+"]"))
    state=set(json.loads("["+grab(r"const STATE=new Set\(\[(.*?)\]\);")+"]"))
    fund=json.loads("{"+grab(r"const SCHOOL_FUND=\{(.*?)\};")+"}")
    alias=json.loads("{"+grab(r"const IALIAS=\{(.*?)\};")+"}")
    return corp,state,fund,alias

def show_person(db,docs,snap_at,name,sch=None):
    rows=[d for d in db if d["n"]==name and (not sch or d["sch"]==sch)]
    if not rows: print("%s：DB0 里没有%s"%(name,"（%s）"%SCH[sch] if sch else ""));
    for d in rows:
        did=hid(d["_id"])
        print("%s（%s）_id=%s  edit 文档 id=%s"%(d["n"],SCH[d["sch"]],d["_id"],did))
        print("   %s%s · %s · %s%s · score %s%s"%(d.get("dept",""),(" › "+d["grp"]) if d.get("grp") else "",d.get("title",""),
              d.get("status",""),(" · 高潜力") if d.get("hot") else "",d.get("score"),(" · manual") if d.get("manual") else ""))
        if d.get("lead"): print("   院长/所长：%s"%d["lead"])
        for c in d.get("cos") or []:
            print("   公司：%s · %s%s%s"%(c["name"],c.get("role",""),(" · "+c["stage"]) if c.get("stage") else "",(" · 投资方 "+"、".join(c["inv"])) if c.get("inv") else ""))
        if d.get("src"): print("   来源：%s"%d["src"])
        ov=[(i,b) for i,b in docs if b.get("kind")=="edit" and b.get("key")==d["_id"]]
        for i,b in ov: print("   ⚠ 快照里有页面编辑 %s（%s）：status=%s%s → 写之前先 read_db get profs/%s，用 --current"%(i,b.get("at"),b["rec"].get("status"),(" hot") if b["rec"].get("hot") else "",i))
    adds=[(i,b) for i,b in docs if b.get("kind")=="add" and b["rec"].get("n")==name and (not sch or b["rec"].get("sch")==sch)]
    for i,b in adds:
        r=b["rec"]; print("   ⚠ 快照里有页面新增 %s（%s）：%s · %s · %s · %s"%(i,b.get("at"),SCH.get(r.get("sch"),"?"),r.get("dept",""),r.get("status",""),"、".join(c["name"] for c in r.get("cos") or []) or "无公司"))
    same=[d for d in db if d["n"]==name]
    if len(same)>1 and not sch: print("   ⚠ 同名 %d 人：%s —— patch 里 sch 必须写对"%(len(same),"、".join(SCH[d["sch"]]+"/"+d.get("dept","") for d in same)))

def show_inv(db,name):
    corp,state,fund,alias=registry()
    canon=alias.get(name,name)
    hits=[(d,c) for d in db for c in d.get("cos") or [] if name in (c.get("inv") or []) or canon in (c.get("inv") or [])]
    tags=[t for t,ok in (("产业资本 CORP",canon in corp),("国资 STATE",canon in state),("校属基金 SCHOOL_FUND",canon in fund)) if ok]
    print("%s%s：DB0 里出现 %d 次%s"%(name,("（规范名 "+canon+"）") if canon!=name else "",len(hits),("；标签："+"、".join(tags)) if tags else "；未登记任何标签"))
    for d,c in hits[:12]: print("   %s（%s）· %s%s"%(d["n"],SCH[d["sch"]],c["name"],(" · "+c["stage"]) if c.get("stage") else ""))
    near=sorted({x for d in db for c in d.get("cos") or [] for x in c.get("inv") or [] if x!=canon and (x in name or name in x or canon in x)})
    if near: print("   ⚠ 相近写法：%s —— 同一家就用已有写法，或加进页面 IALIAS"%"、".join(near))
    if not hits: print("   新机构。若属产业资本 / 国资 / 校属基金，加进页面源码的 CORP / STATE / SCHOOL_FUND（下次发布生效）；否则不用登记。")

def main():
    a=sys.argv[1:]
    if not a: print(__doc__); return
    db=assign_ids(load_db0()); docs,snap_at=snapshot()
    if snap_at: print("（快照 %s：%d 条覆盖文档）"%(snap_at,len(docs)))
    sch=a[a.index("--sch")+1] if "--sch" in a else None
    if "--inv" in a:
        for x in a[a.index("--inv")+1:]:
            if x.startswith("--"): break
            show_inv(db,x)
        return
    for i,x in enumerate(a):
        if x.startswith("--") or (i>0 and a[i-1]=="--sch"): continue
        show_person(db,docs,snap_at,x,sch)

if __name__=="__main__": main()
