#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把五份 md 名录里 AI 相关学院的全部教授/AP 并入 DB0；按四态口径重分状态；高潜力清零后只按 md 明确标注预标。"""
import io,json,re,os,sys
HERE=os.path.dirname(os.path.abspath(__file__)); HTML=os.path.join(HERE,"..","QBFJ AP Network.html")
MD="/Users/ethan/Desktop/四校教授扫描_源码/"
F={"s":"上海交大教授AP扫描_20260828 copy.md","f":"复旦教授AP扫描_20260828 copy.md","t":"清华教授AP扫描_20260829_核实版 copy.md",
   "p":"北大教授AP扫描_20260829 copy.md","q":"北大AI院系教职人员全景扫描_20260829 copy.md"}
T={k:io.open(MD+v,encoding="utf-8").read() for k,v in F.items()}
def sect(t,start,end=None):
    i=t.index(start); j=t.index(end,i+len(start)) if end else len(t); return t[i:j]
def cl(x): return re.sub(r"\*\*|⭐|⚠️|⚠","",x).strip()
def strip_link(x):
    m=re.search(r"\((https?://[^)]+)\)",x); return (m.group(1) if m else re.sub(r"\[|\]","",x).strip())
NAME_OK=re.compile(r"^(?:[一-鿿·]{2,4}|[A-Z][a-zA-Z.]+(?: [A-Z][a-zA-Z.]+){1,2})$")
def split_names(x):
    x=cl(x); out=[]
    for tok in re.split(r"[、，,；;｜|]",x):
        tok=tok.strip()
        if not tok: continue
        note=""; m=re.match(r"^([^（(]+)[（(]([^）)]*)[）)]",tok)
        if m: tok,note=m.group(1).strip(),m.group(2).strip()
        tok=re.sub(r"\s*[/／].*$","",tok).strip()
        if NAME_OK.match(tok) and not re.search(r"人$|^约|等$",tok): out.append((tok,note))
    return out
def rows(tbl):
    rs=[]
    for ln in tbl.split("\n"):
        if not ln.startswith("|"): continue
        c=[cl(x) for x in ln.strip().strip("|").split("|")]
        if all(re.fullmatch(r"-*",x) for x in c) or c[0] in("姓名","人","研究中心","研究所","单位"): continue
        rs.append(c)
    return rs
def fld_of(txt):
    t=txt or ""
    if re.search(r"机器人|具身|操作|抓取|触觉|自动驾驶|人形|无人",t): return "embodied"
    if re.search(r"芯片|集成电路|存算|类脑计算|器件|EDA|半导体",t): return "chip"
    if re.search(r"医|脑|生物|神经|蛋白|药|生命|成像|基因|康复",t): return "bio"
    if re.search(r"量子|能源|聚变|光子|电池",t): return "energy"
    if re.search(r"大模型|语言|NLP|语音|算力|机器学习|深度学习|视觉|智能|推理|数据|系统|检索|图|优化|安全|网络|软件|计算",t): return "ai"
    return "other"
def dsplit(dept):
    """名录 dept →（学院, 研究所/分组）。「人工智能学院（兼聘 PI · 核心领域）」这种括号里带「·」的，
    整段括号才是分组，不能先按「·」切——否则会切出 dept「人工智能学院（兼聘 PI」+ grp「核心领域）」。"""
    m=re.match(r"^(.+?)[（(](.+)[）)]$",dept)
    if m and " · " in m.group(2): return m.group(1).strip(),m.group(2).strip()
    if " · " in dept: b,g=dept.split(" · ",1); return b.strip(),g.strip()
    return dept,""
RS=[]   # (sch, name, dept, title, email, home, research, honor, note, src)
def add(sch,n,dept,title="",email="",home="",research="",honor="",note="",src=""):
    n=cl(n).strip()
    if not NAME_OK.match(n): return
    RS.append(dict(sch=sch,n=n,dept=dept,title=title,email=email,home=home,research=research,honor=honor,note=note,src=src))

# ── 交大 ──
t=T["s"]; s4=sect(t,"## 4. 人工智能学院","## 5. ")
for sub,ttl in (("### 教授（正高）","教授"),("### 副教授","副教授")):
    for c in rows(sect(s4,sub,"###" if sub!="### 副教授" else "### 助理教授")):
        if len(c)>=5: add("s",c[0],"人工智能学院",ttl,c[1],strip_link(c[2]),c[3],"",("" if c[4] in("未见","") else "名录备注："+c[4]),"交大 AI 学院名录 2026-08")
for c in rows(sect(s4,"### 助理教授")):
    if len(c)>=5: add("s",c[0],"人工智能学院",c[1],c[2],strip_link(c[3]),c[4],"","","交大 AI 学院名录 2026-08")
for c in rows(sect(t,"## 5. 计算机学院","## 6. ")):
    if len(c)>=3:
        inst=cl(c[0])
        for nm,note in split_names(c[1]):
            if re.match(r"^[A-Za-z. ]+$",nm): continue          # 外籍中心主任不是 AP 池
            add("s",nm,"计算机学院 · "+inst,"教授（所长/副所长）","","","","",note,"交大计算机学院名录 2026-08")
        for nm,note in split_names(c[2]): add("s",nm,"计算机学院 · "+inst,"教师（名录未给职称）","","","","",note,"交大计算机学院名录 2026-08")
# 交大自动化与感知学院：用户 2026-09-04 决定整院剔除（创业命中率太低），名录不再解析。
# 已创业的王贺升（UniX AI 首席科学家）保留在 DB0，不受影响。
EXCLUDE_DEPT={("s","自动化与感知学院")}
# ── 复旦 ──
t=T["f"]
for c in rows(sect(t,"## 4. 可信具身智能研究院","## 5. ")):
    if len(c)>=2: add("f",c[0],"可信具身智能研究院 TEAI","教师（名录未给职称）","","","", "" if c[1]=="—" else c[1],"","复旦 TEAI 名录 2026-08")
s6=sect(t,"## 6. 计算与智能创新学院","## 7. ")
for lab,ttl in (("教授","教授"),("副教授","副教授"),("青年研究员","青年研究员")):
    m=re.search(r"\*\*%s（[^）]*）\*\*：(.+)"%lab,s6)
    if m:
        for nm,note in split_names(m.group(1)): add("f",nm,"计算与智能创新学院",ttl,"","","","",note,"复旦计算与智能创新学院名录 2026-08")
for c in rows(sect(t,"## 7. 大数据学院","## 8. ")):
    if len(c)>=3: add("f",c[0],"大数据学院",re.split(r"[，,]",c[1])[0],"","",c[2],re.sub(r"^[^，,]*[，,]?","",c[1]),"","复旦大数据学院名录 2026-08")
# ── 清华 ──
t=T["t"]; s41=sect(t,"### 4.1 交叉信息研究院","### 4.2")
for lab,ttl in (("教授","教授"),("长聘副教授","长聘副教授"),("助理教授","助理教授")):
    m=re.search(r"- \*\*%s（\d+）\*\*：(.+)"%lab,s41)
    if m:
        for nm,note in split_names(m.group(1)): add("t",nm,"交叉信息研究院 IIIS",ttl,"","","","",note,"清华 IIIS 名录 2026-08")
s42=sect(t,"### 4.2 人工智能学院","### 4.3")
m=re.search(r"全职 PI（\d+）\*\*：(.+)",s42)
if m:
    for nm,note in split_names(m.group(1)): add("t",nm,"人工智能学院","全职 PI"+("（%s）"%note if note else ""),"","","","","","清华人工智能学院名录 2026-08")
m=re.search(r"兼聘 PI · 核心领域（\d+）\*\*：(.+)",s42)
if m:
    for nm,note in split_names(m.group(1)): add("t",nm,"人工智能学院（兼聘 PI · 核心领域）","兼聘 PI","","","","",note,"清华人工智能学院名录 2026-08")
for c in rows(sect(t,"### 4.3 智能产业研究院","### 4.4")):
    if len(c)>=3: add("t",c[0],"智能产业研究院 AIR",c[1],"","",c[2],"","","清华 AIR 名录 2026-08")
for ln in sect(t,"### 4.4 计算机科学与技术系","## 5. ").split("\n"):
    m=re.match(r"- \*\*(.+?)\*\*[（(]?[^：]*：(.+)",ln)
    if not m: continue
    inst=m.group(1); rest=m.group(2)
    parts=re.split(r"[｜|]副教授：",rest)
    for nm,note in split_names(parts[0]): add("t",nm,"计算机科学与技术系 · "+inst,"教授（名录按所分组）","","","","",note,"清华计算机系名录 2026-08")
    if len(parts)>1:
        for nm,note in split_names(parts[1]): add("t",nm,"计算机科学与技术系 · "+inst,"副教授","","","","",note,"清华计算机系名录 2026-08")
# ── 北大 ──
t=T["p"]
m=re.search(r"教学科研人员（\d+）\*\*：(.+)",sect(t,"### 6.1 前沿计算研究中心","### 6.2"))
if m:
    for nm,note in split_names(m.group(1)): add("p",nm,"前沿计算研究中心 CFCS",note or "教研人员","","","","","","北大 CFCS 名录 2026-08")
for c in rows(sect(t,"### 6.2 人工智能研究院","## 7. ")):
    if len(c)>=2 and c[0]!="其他中心":
        for nm,note in split_names(c[1]): add("p",nm,"人工智能研究院 · "+c[0],"教研人员（名录未给职称）","","","","",note,"北大人工智能研究院名录 2026-08")
q=T["q"]; s4=sect(q,"## 四、全量名册","## 五、")
for blk in re.split(r"\n### ",s4)[1:]:
    head=blk.split("\n",1)[0]; unit=re.sub(r"\s*（\d+ 人）.*$","",head); unit=re.sub(r"（[^）]*）","",unit).strip()
    cross="交叉院系" in head
    for c in rows(blk):
        if cross:
            if len(c)<4 or not re.search(r"信息|计算|智能|电子|软件|工学|集成电路|微纳|自动化|机器人|数据",c[1]): continue
            add("p",c[0],c[1],c[2],c[4] if len(c)>4 and c[4]!="—" else "","",c[3],"","","北大 AI 院系全景 2026-08")
        else:
            if len(c)<3: continue
            bg=c[5] if len(c)>5 and c[5]!="—" else ""; cite=c[6] if len(c)>6 and c[6]!="—" else ""
            honor="；".join(x for x in (bg[:80],cite) if x)
            add("p",c[0],unit,c[1],c[3] if len(c)>3 and c[3]!="—" else "","",c[2],honor,"","北大 AI 院系全景 2026-08")
m=re.search(r"\*\*工学博士生导师（\d+ 人）\*\*：(.+)",sect(q,"## 五、附录 A","## 六、"))
if m:
    for nm,note in split_names(m.group(1)): add("p",nm,"软件与微电子学院","博士生导师","","","","","","北大软微名录 2026-08")
# ── md 明确标注的高潜力：四校 §3 第二梯队 + 北大全景 S/A 档 ──
HOT=set()
def hot_from(txt,sch):
    for c in rows(txt):
        nm=cl(c[0]).split("（")[0].split("(")[0].strip()
        if NAME_OK.match(nm): HOT.add((sch,nm))
    for nm in re.findall(r"\*\*([一-鿿·]{2,4})\*\*",txt): HOT.add((sch,nm))
hot_from(sect(T["s"],"## 3. 第二梯队","## 4. "),"s"); hot_from(sect(T["f"],"## 3. 第二梯队","## 4. "),"f")
hot_from(sect(T["t"],"## 3. 第二梯队","## 4. "),"t"); hot_from(sect(T["p"],"## 3. 第二梯队","## 4. "),"p")
hot_from(sect(q,"### S 档","### B 档"),"p")
# ── 读 DB0，合并 ──
h=io.open(HTML,encoding="utf-8").read()
i=h.index("const DB0=[\n")+len("const DB0=[\n"); j=h.index("\n];",i)
DB=[json.loads(l.strip().rstrip(",")) for l in h[i:j].split("\n") if l.strip()]
idx={(d["sch"],d["n"]):d for d in DB}
seen=set(); added=[]; filled=0
for r in RS:
    k=(r["sch"],r["n"])
    if k in idx:
        d=idx[k]
        base,g=dsplit(r["dept"])
        if g and not d.get("grp"):
            if d["dept"]==base or d["dept"].startswith(base[:4]): d["grp"]=g; filled+=1
        for f in ("email","home"):
            if r[f] and not d.get(f): d[f]=r[f]; filled+=1
        if r["research"] and (not d.get("research") or d["research"].startswith("—")): d["research"]=r["research"]; filled+=1
        continue
    if k in seen: continue
    if (r["sch"],dsplit(r["dept"])[0]) in EXCLUDE_DEPT: continue
    seen.add(k)
    research=r["research"] or "—（名录未给研究方向，待补）"
    d={"n":r["n"],"sch":r["sch"],"dept":r["dept"],"title":r["title"] or "教师（名录未给职称）"}
    d["dept"],g=dsplit(r["dept"])
    if g: d["grp"]=g
    if r["email"]: d["email"]=r["email"]
    if r["home"]: d["home"]=r["home"]
    d["research"]=research
    if r["honor"]: d["honor"]=r["honor"]
    d["fld"]=fld_of(research+" "+r["dept"]) if not research.startswith("—") else fld_of(r["dept"])
    d["status"]="potential"; d["score"]=3
    if r["note"]: d["note"]=r["note"]
    d["src"]=r["src"]; d["cos"]=[]
    DB.append(d); idx[k]=d; added.append(d)
# ── 四态重分（仅原 founded）：正则提议 + 显式判定 ──
GROW=re.compile(r"(?<![A-Za-z])(C\d?\s?轮|C\+|C[1-9]|D\s?轮|D\+|E\s?轮|F\s?轮|B\+|Pre-IPO|IPO|上市|挂牌|收购|港交所|科创板)",re.I)
OVR={("s","张少霆"):("growth","商汤分拆主体，分拆后半年融资 10 亿元，按成熟公司计；报告未给轮次"),
     ("s","王宇光"):("stealth","报告融资栏为「—」，无融资新闻"),("f","李晓鹏"):("stealth","融资未披露，无融资新闻"),
     ("p","董豪"):("stealth","上纬启元为上市公司上纬新材旗下品牌，无独立融资新闻"),
     ("s","陈东坡"):("growth","已完成 9 轮融资，远超 B 轮"),("t","刘知远"):("growth","D+ 轮"),
     ("t","楼天城"):("growth","小马智行 2024.11 纳斯达克上市——报告未载，据公开信息补，请核"),
     ("s","闫维新"):("growth","B 轮后再获腾讯领投战略轮"),("t","陈建宇"):("growth","累计近 50 亿元、国资战略轮、筹备港股 IPO"),
     ("p","王鹤"):("growth","累计融资超 69.6 亿元、估值超 200 亿元"),
     ("s","朱芳芳"):("founded","B1 轮 = B 轮阶段"),("t","张钹"):("founded","B1/B2 = B 轮阶段"),("t","朱军"):("founded","生数 B 轮、瑞莱 B1/B2，均在 B 轮阶段"),
     ("s","金贤敏"):("founded","2026.1 A++ 轮 + B 轮，处于 B 轮阶段")}
recls=[]
for d in DB:
    k=(d["sch"],d["n"])
    if d.get("manual"): continue          # 用户手动判定过的，脚本不得重算
    if d["status"]=="founded":
        if k in OVR:
            st,why=OVR[k]
            if st!="founded": d["status"]=st; d["note"]=(d.get("note","")+"；" if d.get("note") else "")+"状态判定："+why; recls.append((d["n"],st,why))
        else:
            txt=" ".join(c.get("stage","")+" "+c.get("fin","") for c in d.get("cos",[]))
            hits=sorted(set(GROW.findall(txt)))
            if hits: d["status"]="growth"; recls.append((d["n"],"growth","轮次标记 "+"/".join(hits)))
# ── 高潜力：全部清零，只按 md 明确标注预标 ──
cleared=sum(1 for d in DB if d.get("hot"))
# 高潜力默认全不选、由用户手动标；但 manual 记录保留用户自己的标注
for d in DB:
    if not d.get("manual"): d["hot"]=0
hotset=[]
for d in DB:
    if d.get("manual"): continue
    if (d["sch"],d["n"]) in HOT: d["hot"]=1; hotset.append(d["n"])
# ── 写回 ──
ORDER=["n","sch","dept","grp","lead","manual","title","email","home","research","honor","fld","status","hot","score","why","note","src","cos"]
def line(d):
    o={}
    for k in ORDER:
        if k not in d: continue
        v=d[k]
        if v in ("",None) or (k=="hot" and not v): continue
        o[k]=v
    o["cos"]=[{kk:vv for kk,vv in c.items() if vv} for c in d.get("cos",[])]
    return json.dumps(o,ensure_ascii=False,separators=(",",":"))
sk={"s":0,"f":1,"t":2,"p":3}; so={"growth":0,"founded":1,"stealth":2,"potential":3}
DB.sort(key=lambda d:(sk[d["sch"]],so[d["status"]],-d.get("score",0),d["n"]))
h=h[:i]+",\n".join(line(d) for d in DB)+h[j:]
io.open(HTML,"w",encoding="utf-8").write(h)
# ── 汇报 ──
from collections import Counter
print("解析到名录条目 %d，新增 %d 人（补邮箱/主页/方向 %d 处）"%(len(RS),len(added),filled))
print("新增按校：",dict(Counter(d["sch"] for d in added)))
print("DB0 现共 %d 人：%s"%(len(DB),dict(Counter(d["status"] for d in DB))))
print("高潜力：清零 %d → 按 md 标注预标 %d 人：%s"%(cleared,len(hotset),"、".join(sorted(hotset))))
print("状态重分 %d 人："%len(recls)); [print("  %s → %s（%s）"%r) for r in recls]
print("研究方向仍为占位的：%d 人"%sum(1 for d in DB if d["research"].startswith("—")))
