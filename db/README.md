# db 快照说明

**db 本身不在这个文件夹里。** 它是 claude.ai 上挂在 artifact 名下的服务器端文档库
（`capabilities:{db:{}}`），页面里每一次增改都直接写进去，同组织内打开页面的人实时共享。
本地没有任何进程能直接读写它。

这里的 `profs.json` 是它的**快照**：某个时刻把 `profs` 集合整个读出来存成 JSON。
合回 DB0 并清空之前的快照按日期存档在 `merged/`（如 `merged/2026-09-04_profs.json`）；`profs.json` 里 `docs` 为空就说明覆盖层刚被合回。
它不会自动更新。

## 刷新快照

在 Claude Code 里说一句「把 QBFJ AP Network 的 db 快照刷新一下」即可。
Claude 用 Artifact 工具 `read_db`（`collection: "profs"`, `db_op: "list"`）读全集合，写回这个文件。

## 快照里每条记录长什么样

```json
{ "kind": "edit",  "key": "P:s卢策吾", "at": "2026-09-03T…", "rec": { …整条教授记录… } }
{ "kind": "add",   "uid": "fvb9ia713rsj", "at": "…",           "rec": { …新增的人… } }
```
- `edit`：按 `key`（教授 `_id`）整条覆盖源文件 `DB0` 里的那条。
- `add`：新增的人，页面里 id 为 `"N:"+uid`。

## 把改动合回源文件（固化）—— `merge_back.py`

在 Claude Code 里说「合回」或 `/qbfj-sync`，顺序固定：
`read_db list` 写成 `profs.json` → `python3 db/merge_back.py --dry-run` 看清单 → `python3 db/merge_back.py`
→ 发布页面 → `write_db` 批量 delete（脚本会打印清单）→ `python3 db/merge_back.py --clear-snapshot` → commit。

脚本规则：每条合回的记录带 `manual:1`；`edit` 以页面表单字段为准（`grp/lead/manual` 缺失则保留）；
`add` 撞上同校同名的 DB0 行就并进去（名录导入过的人在页面再加一次会撞上），否则追加新行；
`dept` 变了会丢掉旧 `grp`，随后自动跑 `enrich_org.py` 重新拆分（院长/所长不是字段，页面按 `LEADS` 表运行时推算）；校验同页面，不过不写。
合并前的快照按日期存档在 `merged/`。先删文档再发布会让线上短暂丢改动，所以**先发布、再删**。

## 查人 / 查机构 —— `find.py`

```bash
python3 db/find.py 卢策吾 王鹤          # DB0 行、_id、edit 文档 id、快照里的覆盖、同名提醒
python3 db/find.py --sch t 刘洋
python3 db/find.py --inv 顺为资本 高瓴   # 投过谁、规范写法、是否登记了产业资本/国资/校属基金
```

## 本地打开 HTML 时

双击打开的是 `file://`，没有 `window.claude`，页面会退回本浏览器的 localStorage，
工具条上显示红色「仅存本浏览器」。这时的增改和 db 互不相通。
要看到共享数据，请用 artifact 链接打开。

## 贴新闻 → 自动更新（merge_news.py，在 Claude Code 里用 `/qbfj-news`）

流程：把新闻稿贴给 Claude → Claude 认人、抽字段，写成一个小 patch → `merge_news.py` 把 patch
合进该教授的**完整记录**并算出文档 id → Claude 用 Artifact 工具 `write_db set` 写进 `profs`
→ 页面实时刷新，带「已修改」标。不改源文件、不重新发布。

```bash
python3 merge_news.py patch.json                       # 干跑，打印将写入的文档
python3 merge_news.py patch.json --current current.json # 该人已有 db 覆盖时，先 read_db 拿到它再合
```

patch 只写新闻里有的字段（见脚本顶部的注释）。**`hot` 归用户所有，脚本永远不写；`manual:1` 的记录改 `status` 需要 `--force-status`。** 合并规则：
- 标量覆盖；`fin` 追加（用「 → 」连），不会把旧的轮次冲掉
- 公司按中文名头匹配（`穹彻智能` ≈ `穹彻智能 Noematrix`），没有就新增
- 投资方取并集
- 校验与页面 `checkRec()` 同一套，不过就不产出

**每次写之前先 `read_db get profs/<doc_id>`**：如果这个人已经在页面里被改过，要在那个版本上合，
否则会把页面里的改动盖掉。脚本的 `--current` 就是接这个用的。

文档 id 算法（`hid()`）与页面 JS 逐位一致（FNV-1a 32 位，按 code point），已核对。

## 状态口径（2026-09-03 起，用户定义）

| status | 含义 |
|---|---|
| `growth` 成长期项目 | B 轮**以后**的成熟公司（B+ / C / D / IPO / 被收购） |
| `founded` 创业项目 | B 轮**及之前**、有融资新闻 |
| `stealth` 水下项目 | 有项目但**没有融资新闻**（由维护者手动补） |
| `potential` 待创业 | 还没创业 |

`hot` 高潜力与状态正交，**默认全不选**，由维护者手动标；只有 md 报告里明确列为
「第二梯队 / S 档 / A 档」的人在建库时被预标。

~~`rebuild_db0.py`~~：2026-09-04 起**不再从 md 名录批量导入**（用户定：只在页面手改，或贴新闻让 Claude 合），脚本已从仓库删除，最后版本在提交 `08a4937`。新增人：页面「＋ 添加」或贴新闻。
`enrich_org.py`：把合写的院系拆成 `dept` + `grp`、统一别名（幂等）。院长 / 所长不在脚本里：页面源码第一段的 `LEADS` 表（学院→院长）+ 同所职称含「所长」的人，运行时推算；换院长只改 `LEADS`。
`scrape_sjtu.py --refresh`：用缓存页重新解析已抓过的人，覆盖脏的研究方向文本（不上网，`manual` 记录不动）。
