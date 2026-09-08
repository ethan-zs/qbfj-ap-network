#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""交大计算机学院 / 自动化与感知学院 个人页（URL 有固定规律）：抓 职称 / 邮箱 / 研究方向 补进 DB0。确定性抽取，无 LLM。"""
import io,json,re,os,html,sys,time
from concurrent.futures import ThreadPoolExecutor
import urllib.request,urllib.error
from pypinyin import lazy_pinyin
HTML=os.path.join(os.path.dirname(os.path.abspath(__file__)),"..","QBFJ AP Network.html")
CACHE=os.path.join(os.path.dirname(os.path.abspath(__file__)),".cache"); os.makedirs(CACHE,exist_ok=True)
UA="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15"
h=io.open(HTML,encoding="utf-8").read()
i=h.index("const DB0=[\n")+len("const DB0=[\n"); j=h.index("\n];",i)
DB=[json.loads(l.strip().rstrip(",")) for l in h[i:j].split("\n") if l.strip()]
URL={"计算机学院":"https://www.cs.sjtu.edu.cn/jiaoshiml/%s.html"}   # 自动化与感知学院已整院剔除
REFRESH="--refresh" in sys.argv
T=[d for d in DB if d["sch"]=="s" and d["dept"] in URL and re.match(r"^[一-鿿]{2,4}$",d["n"])
   and (REFRESH and "主页抓取" in d.get("src","")
        or d["research"].startswith("—") or not d.get("email") or "名录未给" in d.get("title",""))]
def fetch(d):
    py="".join(lazy_pinyin(d["n"])); url=URL[d["dept"]]%py; fn=os.path.join(CACHE,py+"_"+d["dept"][:2]+".html")
    if os.path.exists(fn): return d,url,io.open(fn,encoding="utf-8",errors="ignore").read()
    try:
        req=urllib.request.Request(url,headers={"User-Agent":UA})
        with urllib.request.urlopen(req,timeout=15) as r:
            if r.status!=200: return d,url,None
            body=r.read().decode("utf-8","ignore")
        io.open(fn,"w",encoding="utf-8").write(body); return d,url,body
    except Exception as e:
        return d,url,None
TITLE=re.compile(r"(长聘教授|特聘教授|讲席教授|长聘副教授|长聘教轨副教授|副教授|助理教授|教授|研究员|副研究员|助理研究员|讲师|博士后)")
STOP=(r"工作经历|工作履历|教育背景|教育经历|个人简介|简介|联系方式|Email|邮箱|荣誉|获奖|学术兼职|代表性|论文|项目|招生|招收|欢迎"
      r"|公众号|二维码|学院地址|资助|担任|Publications|Experience|Education|Research Associate|详见|个人主页")
LEAD=re.compile(r"^(?:主要|目前|长期)?(?:研究方向|研究领域|研究兴趣)?(?:为|是|包括|主要包括|聚焦于|聚焦|涉及|集中于|围绕)?[:：，,\s]*")
def clean_research(rs):
    rs=re.sub(r"[•●▪·]"," ",rs); rs=re.sub(r"\s+"," ",rs)
    rs=LEAD.sub("",rs.strip())
    rs=re.split(STOP,rs)[0]
    rs=re.sub(r"[（(]\s*[）)]","",rs).strip(" ;；,，。、:：")
    return rs
def parse(name,body):
    t=re.sub(r"<script.*?</script>|<style.*?</style>","",body,flags=re.S); t=html.unescape(re.sub(r"<[^>]+>"," ",t)); t=re.sub(r"\s+"," ",t)
    if name not in t: return None
    out={}
    m=re.search(re.escape(name)+r".{0,80}?"+TITLE.pattern,t) or TITLE.search(t)
    if m: out["title"]=m.group(1) if m.lastindex else m.group(0)
    e=re.search(r"[\w.+-]+(?:@|\(at\)|\[at\]|＠)\s?(?:sjtu|cs\.sjtu)\.edu\.cn",t)
    if e:
        m=e.group(0).replace("(at)","@").replace("[at]","@").replace("＠","@").replace(" ","")
        if not re.match(r"^(scs|cs|admin|office|info|hr|contact|xb|bgs|jwc|yjs|master|phd)@",m): out["email"]=m   # 学院公共邮箱（scs@ 等）不是个人邮箱，曾误给 7 人
    r=re.search(r"(?:研究方向|研究领域|研究兴趣|Research Interests?)[:：]?\s*(.+?)(?:"+STOP+r"|$)",t)
    if r:
        rs=clean_research(r.group(1))
        if 4<=len(rs): out["research"]=rs[:110]
    return out
t0=time.time(); ok=0; filled={"title":0,"email":0,"research":0}; miss=[]
with ThreadPoolExecutor(8) as ex:
    for d,url,body in ex.map(fetch,T):
        if not body: miss.append(d["n"]); continue
        p=parse(d["n"],body)
        if not p: miss.append(d["n"]+"?"); continue
        ok+=1
        if p.get("research") and (d["research"].startswith("—") or (REFRESH and not d.get("manual") and p["research"]!=d["research"])):
            d["research"]=p["research"]; filled["research"]+=1
        if p.get("title") and "名录未给" in d.get("title",""): d["title"]=p["title"]; filled["title"]+=1
        if p.get("email") and not d.get("email"): d["email"]=p["email"]; filled["email"]+=1
        if not d.get("home"): d["home"]=url
        if "主页抓取" not in d.get("src",""): d["src"]=(d.get("src","")+"；" if d.get("src") else "")+"主页抓取 2026-09"
ORDER=["n","sch","dept","grp","lead","manual","title","email","home","research","honor","fld","status","hot","score","why","note","src","cos"]
def line(d):
    o={k:d[k] for k in ORDER if k in d and d[k] not in ("",None) and not (k=="hot" and not d[k])}
    o["cos"]=[{kk:vv for kk,vv in c.items() if vv} for c in d.get("cos",[])]
    return json.dumps(o,ensure_ascii=False,separators=(",",":"))
h=h[:i]+",\n".join(line(d) for d in DB)+h[j:]
io.open(HTML,"w",encoding="utf-8").write(h)
print("目标 %d 人，抓到 %d 页，%.0fs；补 研究方向 %d · 职称 %d · 邮箱 %d；未抓到 %d：%s"%(len(T),ok,time.time()-t0,filled["research"],filled["title"],filled["email"],len(miss),"、".join(miss[:40])+("…" if len(miss)>40 else "")))
