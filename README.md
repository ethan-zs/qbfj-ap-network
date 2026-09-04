# 清北复交 AP Network

四校（上海交大 / 复旦 / 清华 / 北大）AI 相关院系教授与 AP 的创业库。

**页面（实时协作版）**：https://claude.ai/code/artifact/211e3d3e-7d7f-4de5-adcb-1625832c1ff4

## 这个仓库是什么

源码与数据的**版本管理**。实时编辑不在这里——在上面那个 artifact 链接里，
页面内的增改存在 claude.ai 的 artifact db（集合 `profs`），同组织内实时共享。

本仓库 = 基线数据 + 构建脚本 + 某一时刻的 db 快照。

```
QBFJ AP Network.html   页面本体（单文件，内含 DB0 基线数据）
交接说明.md             17 节：设计约束、数据口径、踩过的坑。改之前先读这个
db/
  README.md            db 是什么、怎么把页面里的改动合回源文件
  profs.json           artifact db 的快照（不自动更新）
  rebuild_db0.py       从 md 名录并入 DB0
  enrich_org.py        规范学院、补研究所与院长
  scrape_sjtu.py       抓交大个人页补研究方向/职称/邮箱
  merge_news.py        把一条融资新闻合进某位教授的记录
```

## 数据模型

一位教授一个对象，`DB0` 是文件里写死的基线，页面内的增改是叠在上面的覆盖层。
状态四态：`growth` 成长期（B 轮后）· `founded` 创业项目（≤B 轮有融资新闻）·
`stealth` 水下（有项目无融资新闻）· `potential` 待创业。`hot` 高潜力由维护者手动标。

字段说明见 `QBFJ AP Network.html` 顶部 `DB0` 上方的注释块。

## 脚本顺序

```bash
python3 db/rebuild_db0.py && python3 db/enrich_org.py && python3 db/scrape_sjtu.py
```

**必须按这个顺序。** 详见交接说明 §15。

## ⚠️ 保持私有

含 939 位教授的姓名、职务邮箱，以及本库自行判断的创业可能性评分与「高潜力」标注。
评分与标注是内部判断，不是官方口径。不要公开这个仓库。
