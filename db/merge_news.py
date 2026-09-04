#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
把一条「新闻抽取结果」合进某位教授的完整记录，产出 write_db 需要的 (doc_id, body)。

用法：
  python3 merge_news.py patch.json            # 干跑：打印将要写入的文档
  python3 merge_news.py patch.json --current current.json   # 该人已有 db 覆盖时，把它传进来作为合并基底

patch.json 的形状（只写新闻里有的字段，其余不用碰）：
{
  "n": "卢策吾", "sch": "s",                  # 必填，用来定位人；新人也填这两个
  "status": "founded", "score": 5,  # 可选。hot 归用户所有，patch 里写了也会被忽略
  "note": "…", "why": "…", "src": "36氪 2026-09-03",
  "cos": [ { "name": "穹彻智能 Noematrix", "role": "联合创始人",
             "stage": "A 轮", "born": "2023.11",
             "fin": "2026.9 A 轮 3 亿元，红杉领投",          # 会【追加】到已有融资口径后面
             "inv": ["红杉中国", "高瓴"] } ]                    # 与已有投资方【并集】
}
规则：
  - 标量字段：新闻里有就覆盖（fin 例外：追加，用「 → 」连接）
  - cos 按公司名匹配（中文名头相同即视为同一家）；没有就新增一家
  - status 四态：growth 成长期(B 轮以后) / founded 创业项目(B 轮及之前有融资新闻) / stealth 水下(无融资新闻) / potential 待创业
  - growth/founded 则 score 固定 5；挂着公司的人不能是 potential（自动改 stealth）
  - 新闻里轮次是 B+/C/D/IPO/被收购 → 写 status:"growth"；B 轮及之前 → "founded"
  - 校验规则与页面 checkRec() 一致，不过就不产出
"""
import io,json,re,sys,os,time,random

HTML=os.path.join(os.path.dirname(os.path.abspath(__file__)),"..","QBFJ AP Network.html")
SCH={"s":"上海交通大学","f":"复旦大学","t":"清华大学","p":"北京大学"}
FLD=["embodied","ai","chip","bio","energy","other"]
STAT=["growth","founded","stealth","potential"]

def load_db0():
    h=io.open(HTML,encoding="utf-8").read()
    i=h.index("const DB0=[\n")+len("const DB0=[\n"); j=h.index("\n];",i)
    out=[]
    for line in h[i:j].split("\n"):
        line=line.strip().rstrip(",")
        if line: out.append(json.loads(line))
    return out

def pid(d): return "P:"+d["sch"]+d["n"]
def assign_ids(db):                       # 与页面 assignIds() 同一算法：同校重名加 #2 #3
    seen=set()
    for d in db:
        if d.get("_id","").startswith("N:"): seen.add(d["_id"]); continue
        k=pid(d); n=1
        while k in seen: n+=1; k=pid(d)+"#"+str(n)
        d["_id"]=k; seen.add(k)
    return db

def hid(s):                               # 与页面 hid() 逐位一致：FNV-1a 32 位，按 code point
    h=2166136261
    for ch in s:
        h^=ord(ch); h=(h*16777619)&0xFFFFFFFF
    return "p"+format(h,"x")

def head(nm):
    o=[]
    for ch in nm:
        if ch in " \t（(/·，,：:" or ord(ch)<128: break
        o.append(ch)
    return "".join(o) or nm

def check(d):
    m=[k for k in ["n","sch","dept","title","research","fld","status"] if not d.get(k)]
    if d.get("fld") and d["fld"] not in FLD: m.append("fld 非法")
    if d.get("status") and d["status"] not in STAT: m.append("status 非法")
    if not (1<=int(d.get("score") or 0)<=5): m.append("score 必须 1-5")
    cos=d.get("cos") or []
    if d.get("status") in ("growth","founded") and not cos: m.append("创业/成长期项目却没有公司")
    for c in cos:
        if not c.get("name"): m.append("有公司没写名字")
        elif not c.get("role"): m.append("公司「%s」没写角色"%c["name"])
    return m

# 「用户手动改的一律照用户的来」（2026-09-04 定）：
#   · hot 完全归用户，任何 patch 都不写
#   · manual 记录的 status 不被 patch 覆盖，除非命令行显式 --force-status
USER_OWNED={"hot","manual"}
def merge(base,patch):
    d=json.loads(json.dumps(base))
    for k,v in patch.items():
        if k in ("cos","_id","n","sch"): continue
        if k in USER_OWNED: continue
        if k=="status" and d.get("manual") and "--force-status" not in sys.argv:
            if v!=d.get("status"):
                print("  · 保留用户手动状态「%s」（新闻建议 %s；要覆盖加 --force-status）"%(d.get("status"),v))
            continue
        if v not in (None,""): d[k]=v
    cos=d.get("cos") or []
    for pc in patch.get("cos") or []:
        if not pc.get("name"): continue
        tgt=next((c for c in cos if head(c["name"])==head(pc["name"]) or c["name"]==pc["name"]),None)
        if not tgt:
            tgt={"name":pc["name"],"role":pc.get("role","")}; cos.append(tgt)
        for k in ("role","born","stage"):
            if pc.get(k): tgt[k]=pc[k]
        if pc.get("fin"):
            tgt["fin"]=(tgt.get("fin","")+" → "+pc["fin"]) if tgt.get("fin") and pc["fin"] not in tgt["fin"] else pc["fin"]
        inv=list(tgt.get("inv") or [])
        for x in pc.get("inv") or []:
            if x and x not in inv: inv.append(x)
        if inv: tgt["inv"]=inv
    d["cos"]=cos
    if d["cos"] and d.get("status")=="potential" and not d.get("manual"): d["status"]="stealth"
    if d.get("status") in ("growth","founded"): d["score"]=5
    d["hot"]=1 if d.get("hot") else 0          # 只做归一，值始终来自用户
    return d

def clean(d):
    keep=["n","sch","dept","manual","title","email","home","research","honor","fld","status","hot","score","why","note","src","cos"]
    r={k:d[k] for k in keep if k in d and d[k] not in (None,"") and not (k=="hot" and not d[k])}
    r["cos"]=[{k:v for k,v in c.items() if v} for c in (d.get("cos") or []) if c.get("name")]
    if not r["cos"]: del r["cos"]
    return r

def main():
    args=sys.argv[1:]
    if not args: print(__doc__); sys.exit(1)
    patch=json.load(io.open(args[0],encoding="utf-8"))
    current=None
    if "--current" in args:
        current=json.load(io.open(args[args.index("--current")+1],encoding="utf-8"))
    db=assign_ids(load_db0())
    base=next((d for d in db if d["n"]==patch["n"] and d["sch"]==patch["sch"]),None)
    now=time.strftime("%Y-%m-%dT%H:%M:%S")
    if base:
        if current and current.get("kind")=="edit" and current.get("key")==base["_id"]:
            base=dict(current["rec"],_id=base["_id"])          # 已有 db 覆盖 → 在它之上合
        merged=merge(base,patch); kind="edit"
        doc_id=hid(base["_id"]); body={"kind":"edit","key":base["_id"],"at":now,"rec":clean(merged)}
    else:
        if current and current.get("kind")=="add":
            uid=current["uid"]; base=dict(current["rec"])
        else:
            uid="".join(random.choice("abcdefghijklmnopqrstuvwxyz0123456789") for _ in range(8))+format(int(time.time()),"x")[-4:]
            base={"n":patch["n"],"sch":patch["sch"],"dept":"","title":"","research":"","fld":"other",
                  "status":"potential","hot":0,"score":3,"cos":[]}
        merged=merge(base,patch); kind="add"
        doc_id="n"+uid; body={"kind":"add","uid":uid,"at":now,"rec":clean(merged)}
    errs=check(body["rec"])
    if errs:
        print("✗ 还不能写入："+"；".join(errs)); print(json.dumps(body,ensure_ascii=False,indent=1)); sys.exit(2)
    print("✓ %s %s（%s）→ profs/%s"%(kind,patch["n"],SCH[patch["sch"]],doc_id))
    print(json.dumps({"collection":"profs","doc_id":doc_id,"data":body},ensure_ascii=False,indent=1))

if __name__=="__main__": main()
