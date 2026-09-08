#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
把 claude.ai db 覆盖层（profs 集合的快照）合回源文件里的 DB0。

用法：
  python3 merge_back.py                        # 读 db/profs.json → 合进 ../QBFJ AP Network.html → 存档快照 → 跑 enrich_org.py
  python3 merge_back.py --dry-run              # 只打印会发生什么，不写任何文件
  python3 merge_back.py 某快照.json --html 某页面.html --no-enrich     # 指定输入 / 输出（测试用）
  python3 merge_back.py --clear-snapshot       # db 里的文档删完之后，把 profs.json 重置为空集

完整顺序见 db/README.md「合回」：
  read_db list → 写 profs.json → 本脚本 → 发布 → write_db 批量 delete（脚本会打印清单）→ --clear-snapshot → commit

规则（§18.4 + 2026-09-04 第一次合回时定下的）：
  - 合回的每条记录一律带 manual:1。
  - edit：按 key 找到 DB0 行。页面表单能改的字段以 rec 为准（rec 里没有 = 用户清空了，包括 hot）；
    grp / manual 两个字段早期文档没有，rec 没有就保留 DB0 的；
    rec.dept 等于「dept + 空格/· + grp」的合写形式时视为没改 dept。
  - add：同校同名已在 DB0（名录导入后常见）→ 合并进那一行：rec 有的字段覆盖，没有的保留；
    honor 取超集或用「；」拼接；hot 只加不减；公司按中文名头匹配、投资方取并集。
    DB0 里没有 → 追加为新行。
  - dept 变了就丢掉旧的 grp，交给 enrich_org.py 重新拆分。院长 / 所长不是字段，页面运行时按 LEADS 表推算。
  - 校验与页面 checkRec 一致，不过就不写（--force 可硬写，页面会在控制台点名）。
"""
import io,json,os,sys,shutil,subprocess,time
HERE=os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0,HERE)
from merge_news import assign_ids,check,head          # 与贴新闻脚本共用 id 算法与校验
HTML_DEFAULT=os.path.normpath(os.path.join(HERE,"..","QBFJ AP Network.html"))
SNAP_DEFAULT=os.path.join(HERE,"profs.json")
ARTIFACT="https://claude.ai/code/artifact/211e3d3e-7d7f-4de5-adcb-1625832c1ff4"
ORDER=["n","sch","dept","grp","manual","title","email","home","research","honor","fld","status","hot","score","why","note","src","cos"]
DROP={"lead"}                                          # 旧字段：2026-09-04 起院长/所长由页面运行时推算，快照里若还有就丢掉
PAGE_EDITABLE=["n","sch","dept","title","email","home","research","honor","fld","status","hot","score","why","note","src","cos"]
SCH={"s":"上海交通大学","f":"复旦大学","t":"清华大学","p":"北京大学"}

def load_html(path):
    h=io.open(path,encoding="utf-8").read()
    i=h.index("const DB0=[\n")+len("const DB0=[\n"); j=h.index("\n];",i)
    raw=[l for l in h[i:j].split("\n") if l.strip()]
    db=[json.loads(l.strip().rstrip(",")) for l in raw]
    return h,i,j,raw,db

def load_snapshot(path):
    s=json.load(io.open(path,encoding="utf-8"))
    docs=s.get("docs",s) if isinstance(s,dict) and "docs" in s else s
    out=[]
    if isinstance(docs,dict): items=docs.items()
    else: items=[(x.get("id"),x) for x in docs]
    for did,b in items:
        data=b.get("data",b) if isinstance(b,dict) else b
        if isinstance(data,dict) and data.get("rec"): out.append((did,data))
    out.sort(key=lambda x:str(x[1].get("at","")))         # 旧的先合，新的赢
    return out,(s.get("snapshotAt") if isinstance(s,dict) else None)

def line(d):
    for k in DROP: d.pop(k,None)
    extra=set(d)-set(ORDER)-{"_id"}
    if extra: raise SystemExit("✗ %s 有未知字段 %s，不写"%(d.get("n"),sorted(extra)))
    o={k:d[k] for k in ORDER if k in d and d[k] not in ("",None) and not (k=="hot" and not d[k])}
    o["cos"]=[{kk:vv for kk,vv in c.items() if vv} for c in d.get("cos") or [] if c.get("name")]
    return json.dumps(o,ensure_ascii=False,separators=(",",":"))

def norm_cos(cos): return [{k:v for k,v in c.items() if v} for c in (cos or []) if c and c.get("name")]
def dept_same(row,rec):
    rd=rec.get("dept")
    if not rd or rd==row.get("dept"): return True
    g=row.get("grp")
    return bool(g) and rd in (row["dept"]+" "+g,row["dept"]+" · "+g,row["dept"]+"·"+g)
def merge_honor(old,new):
    if not old: return new
    if not new: return old
    if new in old: return old
    if old in new: return new
    return new+"；"+old
def merge_cos(old,new):
    cos=norm_cos(old)
    for pc in norm_cos(new):
        tgt=next((c for c in cos if c["name"]==pc["name"] or head(c["name"])==head(pc["name"])),None)
        if not tgt: cos.append(dict(pc)); continue
        for k,v in pc.items():
            if k=="name": continue                 # 名头匹配上就沿用 DB0 的写法：公司节点按全名聚合，改名会把同一家裂成两个
            if k=="inv":
                inv=list(tgt.get("inv") or []); inv+=[x for x in v if x not in inv]; tgt["inv"]=inv
            elif k=="fin" and tgt.get("fin") and v!=tgt["fin"] and v not in tgt["fin"]:
                tgt["fin"]=tgt["fin"]+" → "+v
            else: tgt[k]=v
    return cos

def apply_edit(row,rec):
    """页面编辑：表单字段以 rec 为准；grp/lead/manual 缺失则保留；dept 合写形式视为没改。"""
    if rec.get("n")!=row["n"] or rec.get("sch")!=row["sch"]: return "✗ rec 的姓名/学校与 key 指向的行不一致，跳过"
    same=dept_same(row,rec); new={"_id":row["_id"]}
    for k in PAGE_EDITABLE:
        if k=="dept": new["dept"]=row["dept"] if same else rec["dept"]
        elif k=="hot":
            if rec.get("hot"): new["hot"]=1
        elif k=="cos": new["cos"]=norm_cos(rec.get("cos"))
        elif rec.get(k) not in ("",None): new[k]=rec[k]
    for k in ("grp",):
        if rec.get(k): new[k]=rec[k]
        elif same and row.get(k): new[k]=row[k]
    new["manual"]=1
    row.clear(); row.update(new); return "edit 合回"

def apply_add_into(row,rec):
    """add 撞上同校同名的 DB0 行：rec 有的覆盖，没有的保留；honor 超集；hot 只加不减。"""
    same=dept_same(row,rec); new=dict(row)
    for k in PAGE_EDITABLE:
        if k in ("n","sch"): continue
        if k=="dept":
            if not same: new["dept"]=rec["dept"]
        elif k=="hot":
            if rec.get("hot"): new["hot"]=1
        elif k=="cos":
            if rec.get("cos"): new["cos"]=merge_cos(row.get("cos"),rec["cos"])
        elif k=="honor":
            if rec.get("honor"): new["honor"]=merge_honor(row.get("honor"),rec["honor"])
        elif rec.get(k) not in ("",None): new[k]=rec[k]
    if not same:
        for k in ("grp",): new.pop(k,None)
    for k in ("grp",):
        if rec.get(k): new[k]=rec[k]
    new["manual"]=1
    row.clear(); row.update(new); return "add 并入同校同名行"

def new_row(rec):
    new={k:v for k,v in rec.items() if k in ORDER and v not in ("",None)}
    new["cos"]=norm_cos(rec.get("cos"))
    if not rec.get("hot"): new.pop("hot",None)
    new.setdefault("src","页面内添加")
    new.setdefault("score",5 if new.get("status") in ("growth","founded") else 3)
    new["manual"]=1
    return new

def full_check(d):
    m=check(d)
    if d.get("status")=="potential" and (d.get("cos") or []): m.append("待创业却挂了公司（应为水下项目）")
    return m

def short(v):
    s=json.dumps(v,ensure_ascii=False) if not isinstance(v,str) else v
    return s if len(s)<=70 else s[:67]+"…"
def diff(old,new):
    out=[]
    for k in ORDER:
        a,b=old.get(k),new.get(k)
        if k=="hot": a,b=(1 if a else None),(1 if b else None)
        if a!=b: out.append("      %-8s %s → %s"%(k,short(a) if a not in (None,"",[]) else "∅",short(b) if b not in (None,"",[]) else "∅"))
    return out

def clear_snapshot():
    io.open(SNAP_DEFAULT,"w",encoding="utf-8").write(json.dumps({"artifact":ARTIFACT,"collection":"profs",
        "snapshotAt":time.strftime("%Y-%m-%dT%H:%M:%S"),
        "note":"artifact db 的快照，不自动更新。刷新方式见本目录 README.md。覆盖层已合回 DB0（见 merged/），当前集合为空。",
        "docs":[]},ensure_ascii=False,indent=1)+"\n")
    print("profs.json 已重置为空集")

def main():
    args=sys.argv[1:]
    if "--clear-snapshot" in args: clear_snapshot(); return
    dry="--dry-run" in args; force="--force" in args; no_enrich="--no-enrich" in args
    html_path=args[args.index("--html")+1] if "--html" in args else HTML_DEFAULT
    pos=[a for i,a in enumerate(args) if not a.startswith("--") and (i==0 or args[i-1]!="--html")]
    snap_path=pos[0] if pos else SNAP_DEFAULT
    docs,snap_at=load_snapshot(snap_path)
    print("快照 %s（%s）：%d 条文档 · 页面 %s"%(os.path.relpath(snap_path),snap_at or "无时间",len(docs),os.path.relpath(html_path)))
    if not docs: print("覆盖层为空，没有要合的。"); return
    h,i,j,raw,db=load_html(html_path)
    for d in db: d.setdefault("cos",[])
    assign_ids(db)
    by_id={d["_id"]:k for k,d in enumerate(db)}
    before={k:json.loads(json.dumps(d)) for k,d in enumerate(db)}
    touched=[]; appended=[]; log=[]; dels=[]
    for did,body in docs:
        rec=body["rec"]; kind=body.get("kind")
        if kind=="edit":
            k=by_id.get(body.get("key"))
            if k is None: log.append("  ✗ %s edit key=%s 在 DB0 里找不到，跳过（不删这条文档）"%(did,body.get("key"))); continue
            msg=apply_edit(db[k],rec)
            if msg.startswith("✗"): log.append("  %s %s"%(did,msg)); continue
            touched.append(k); dels.append(did); log.append("  · %s %s（%s）%s"%(did,rec.get("n"),SCH.get(rec.get("sch"),"?"),msg))
        elif kind=="add":
            k=next((x for x,d in enumerate(db) if d["sch"]==rec.get("sch") and d["n"]==rec.get("n")),None)
            if k is not None:
                msg=apply_add_into(db[k],rec); touched.append(k)
            else:
                d=new_row(rec); db.append(d); k=len(db)-1; appended.append(k); msg="add 追加为新行"
            dels.append(did); log.append("  · %s %s（%s）%s"%(did,rec.get("n"),SCH.get(rec.get("sch"),"?"),msg))
        else: log.append("  ✗ %s kind=%s 不认识，跳过"%(did,kind))
    print("\n".join(log))
    assign_ids(db)
    changed=[k for k in sorted(set(touched)) if json.dumps(db[k],ensure_ascii=False,sort_keys=True)!=json.dumps(before[k],ensure_ascii=False,sort_keys=True)]
    print("\n改动 %d 行 · 新增 %d 行 · 可删文档 %d 条"%(len(changed),len(appended),len(dels)))
    for k in changed:
        print("   %s（%s）"%(db[k]["n"],SCH[db[k]["sch"]])); print("\n".join(diff(before[k],db[k])))
    for k in appended:
        print("   + %s（%s）%s · %s · %s"%(db[k]["n"],SCH.get(db[k]["sch"],"?"),db[k].get("dept",""),db[k].get("status",""),"、".join(c["name"] for c in db[k]["cos"]) or "无公司"))
    errs=[(db[k]["n"],full_check(db[k])) for k in sorted(set(changed+appended))]
    errs=[(n,m) for n,m in errs if m]
    if errs:
        print("\n✗ 校验不过：\n"+"\n".join("   %s → %s"%(n,"；".join(m)) for n,m in errs))
        if not force: print("  没有写文件。改好快照再来，或加 --force 硬写（页面控制台会点名）。"); sys.exit(2)
    if dry: print("\n--dry-run：没有写文件。"); return
    if not changed and not appended:
        print("DB0 没有变化（这些文档的内容已经在源文件里）。")
    else:
        out=[line(db[k]) if k in set(changed+appended) else raw[k].rstrip(",") for k in range(len(raw))]
        out+=[line(db[k]) for k in appended]
        io.open(html_path,"w",encoding="utf-8").write(h[:i]+",\n".join(out)+h[j:])
        print("已写入 %s"%os.path.relpath(html_path))
    if snap_path==SNAP_DEFAULT:
        os.makedirs(os.path.join(HERE,"merged"),exist_ok=True)
        base=time.strftime("%Y-%m-%d")+"_profs"; dst=os.path.join(HERE,"merged",base+".json"); n=2
        while os.path.exists(dst) and io.open(dst,encoding="utf-8").read()!=io.open(snap_path,encoding="utf-8").read():
            dst=os.path.join(HERE,"merged","%s_%d.json"%(base,n)); n+=1
        shutil.copyfile(snap_path,dst); print("快照已存档 → %s"%os.path.relpath(dst))
    if not no_enrich and (changed or appended):
        if os.path.normpath(html_path)==HTML_DEFAULT:
            print("跑 enrich_org.py 补 dept/grp/lead …"); subprocess.run([sys.executable,os.path.join(HERE,"enrich_org.py")],check=True)
        else: print("（--html 指向非默认页面，跳过 enrich_org.py）")
    print("\n下一步：\n  1. 发布页面（Artifact publish，带 url，不传 capabilities）\n  2. 发布成功后删掉这些文档（write_db batch）：")
    print("     "+json.dumps([{"op":"delete","collection":"profs","doc_id":d} for d in dels],ensure_ascii=False))
    print("  3. python3 db/merge_back.py --clear-snapshot ，然后 commit")

if __name__=="__main__": main()
