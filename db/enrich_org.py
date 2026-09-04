#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""组织谱系：dept 拆成 学院(dept) + 研究所/中心(grp)，挂上 院长/所长(lead)；剔除所长栏扫进来的外籍中心主任。"""
import io,json,re,os
HTML=os.path.join(os.path.dirname(os.path.abspath(__file__)),"..","QBFJ AP Network.html")
h=io.open(HTML,encoding="utf-8").read()
i=h.index("const DB0=[\n")+len("const DB0=[\n"); j=h.index("\n];",i)
DB=[json.loads(l.strip().rstrip(",")) for l in h[i:j].split("\n") if l.strip()]
ALIAS={"s":{"机动学院":"机械与动力工程学院","电院":"电子信息与电气工程学院","电气工程系":"电子信息与电气工程学院",
           "计算机学院（含网络空间安全学院、密码学院）":"计算机学院","船建学院":"船舶海洋与建筑工程学院","生医工":"生物医学工程学院",
           "原上海交大（已离校专职创业）":"已离校","报告未写明院系":"未注明学院","材料学院":"材料科学与工程学院"},
       "t":{"计算机系":"计算机科学与技术系","人工智能学院（兼聘 PI":"人工智能学院","交叉信息研究院 IIIS；兼聘人工智能学院":"交叉信息研究院 IIIS","IIIS":"交叉信息研究院 IIIS","交叉信息研究院":"交叉信息研究院 IIIS","智能产业研究院":"智能产业研究院 AIR","AIR":"智能产业研究院 AIR",
           "电子系":"电子工程系","电子工程系主任":"电子工程系"},
       "p":{"前沿计算研究中心":"前沿计算研究中心 CFCS","人工智能研究院跨聘":"人工智能研究院","人工智能研究院 × 集成电路学院":"集成电路学院","前沿计算研究中心（CFCS）":"前沿计算研究中心 CFCS","报告未写明院系":"未注明学院","电子学院":"电子学院","CFCS":"前沿计算研究中心 CFCS","王选计算机研究所 WICT":"王选计算机研究所","智能科学系":"智能学院","信息科学技术学院":"信息科学技术学院"},
       "f":{"计算与智能创新学院（原计算机科学技术学院）":"计算与智能创新学院","类脑智能研究院":"类脑智能科学与技术研究院","类脑智能科学与技术研究院 ISTBI":"类脑智能科学与技术研究院","报告未写明院系":"未注明学院","报告未写明":"未注明学院","上海创智学院":"上海创智学院（非复旦教职）",
           "可信具身智能研究院":"可信具身智能研究院 TEAI","TEAI":"可信具身智能研究院 TEAI"}}
LEADS={("t","交叉信息研究院 IIIS"):"姚期智（院长）",("t","人工智能学院"):"姚期智（院长）",
       ("t","智能产业研究院 AIR"):"张亚勤（创始院长）· 刘洋（院长）",
       ("p","智能学院"):"朱松纯（院长）",("p","人工智能研究院"):"朱松纯（院长）",("p","前沿计算研究中心 CFCS"):"高文 · John E. Hopcroft（主任）",
       ("s","人工智能学院"):"王延峰（执行院长）· 张娅（副院长）",
       ("f","可信具身智能研究院 TEAI"):"姜育刚（牵头）",("f","大数据学院"):"冯建峰（院长）",("f","类脑智能科学与技术研究院"):"冯建峰（院长）",
       ("f","智能机器人研究院"):"甘中学（院长）",("f","通用物理智能研究院"):"苏昊（院长）",("f","智能机器人与先进制造创新学院"):"甘中学"}
SUB=re.compile(r"研究院|研究所|中心|实验室|兼聘|研究组|成员|TEAI|PI|系$|所$")
def split(sch,dept):
    d=re.split(r"[；;]",dept.strip())[0].strip(); g=""
    if d.startswith("（") or d.startswith("("): d=d.strip("（）()")
    m=re.match(r"^(.+?)[（(](.+)[）)]$",d)                      # 括号里是子单位 → 先拆括号，别被括号里的「·」骗
    if m and SUB.search(m.group(2)): d,g=m.group(1).strip(),m.group(2).strip()
    else:
        for sep in (" · ","·"," / ","／","/"):
            if sep in d: d,g=[x.strip() for x in d.split(sep,1)]; break
    m=re.match(r"^计算机系\s+(.+)$",d)
    if sch=="t" and m and not g: d,g="计算机科学与技术系",m.group(1)
    m=re.match(r"^(\S+?(?:学院|研究院|系|中心))\s+(\S+(?:研究所|中心|实验室|研究院|学院))$",d)   # 「人工智能研究院 计算机视觉研究中心」
    if m and not g: d,g=m.group(1),m.group(2)
    m=re.match(r"^(.+?)[（(](.+)[）)]$",d)                       # 剩下的括号是头衔/备注，不是子单位 → 丢掉
    if m and not SUB.search(m.group(2)): d=m.group(1).strip()
    d=re.sub(r"[⚠️\s]+$","",d)
    if sch=="s" and d.startswith("材料"): d="材料科学与工程学院"
    if sch=="s" and d.startswith("原副教授"): d="已离校"
    d=ALIAS.get(sch,{}).get(d,d)
    if g and not re.search(r"所|中心|室|院|系|组|PI|领域",g): g=g+"研究中心" if sch=="p" and "人工智能研究院" in d else g
    return d,g
dropped=[]
keep=[]
for d in DB:
    if re.match(r"^[A-Za-z. ]+$",d["n"]) and "所长" in d.get("title","") and not d.get("cos"):
        dropped.append(d["n"]); continue
    keep.append(d)
DB=keep
for d in DB:
    dept,grp=split(d["sch"],d["dept"]); d["dept"]=dept
    if grp: d["grp"]=grp                       # 拆出新的才覆盖；dept 已干净时保留原有 grp（幂等）
# 交大计算机学院各所的所长：从名录里 title 含「所长」的人反推
grp_leads={}
for d in DB:
    if "所长" in d.get("title","") and d.get("grp"): grp_leads.setdefault((d["sch"],d["dept"],d["grp"]),[]).append(d["n"])
for d in DB:
    lead=LEADS.get((d["sch"],d["dept"]))
    gl=grp_leads.get((d["sch"],d["dept"],d.get("grp","")))
    if gl and d["n"] not in gl: lead=("、".join(gl)+"（所长）")+("　·　"+lead if lead else "")
    if lead and d["n"] not in lead: d["lead"]=lead
    elif "lead" in d: del d["lead"]
ORDER=["n","sch","dept","grp","lead","manual","title","email","home","research","honor","fld","status","hot","score","why","note","src","cos"]
def line(d):
    o={k:d[k] for k in ORDER if k in d and d[k] not in ("",None) and not (k=="hot" and not d[k])}
    o["cos"]=[{kk:vv for kk,vv in c.items() if vv} for c in d.get("cos",[])]
    return json.dumps(o,ensure_ascii=False,separators=(",",":"))
h=h[:i]+",\n".join(line(d) for d in DB)+h[j:]
# 字段文档
h=h.replace("     dept*     院系 / 研究机构        title*  职称",
            "     dept*     学院（学校下一级；网络图按它分层）   grp  研究所 / 中心 / 实验室（学院下一级）\n     lead      该学院 / 研究所的院长 / 所长（用于「同门」展示）   title*  职称")
io.open(HTML,"w",encoding="utf-8").write(h)
from collections import Counter
print("dropped:",dropped)
print("DB0:",len(DB),"| with grp:",sum(1 for d in DB if d.get("grp")),"| with lead:",sum(1 for d in DB if d.get("lead")))
for s in "sftp":
    c=Counter(d["dept"] for d in DB if d["sch"]==s)
    print(" ",s,len(c),"depts:",", ".join("%s(%d)"%kv for kv in c.most_common(9)),"…" if len(c)>9 else "")
