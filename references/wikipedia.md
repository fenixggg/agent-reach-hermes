# Wikipedia + Wikidata 抓取 — 官方 API（免密钥、免登录）

**两个渠道同属维基媒体，都是官方 API，都无需 API key、无需注册。** 这是 agent-reach 里唯一的「零凭证 + 有官方文档 + 有 SLA 保障」组合，且**天然配对使用**：

- **Wikipedia** = 条目正文（散文式知识）
- **Wikidata** = 结构化事实（实体编号 + 属性值）——`summary` 返回的 `wikibase_item` 就是 Wikidata 的 Q 编号，可直接喂过去

| API | 端点 | 特点 |
|-----|------|------|
| **REST API**（推荐入口） | `https://{lang}.wikipedia.org/api/rest_v1/` | 语义清晰、JSON 友好、适合摘要/单条取数 |
| **Action API**（MediaWiki） | `https://{lang}.wikipedia.org/w/api.php` | 能力最强（搜索/解析/跨语言），参数多但可精确控制 |
| **Wikidata Action API** | `https://www.wikidata.org/w/api.php` | 实体检索/批量标签 |
| **Wikidata SPARQL** | `https://query.wikidata.org/sparql` | 任意关系查询（正文里没有的结构化事实） |

**全部不需要认证。** 唯一强制要求：带符合 [Wikimedia UA policy](https://foundation.wikimedia.org/wiki/Policy:User-Agent_policy) 的 `User-Agent`（须含联系方式）。

## ⚠️ 必须带代理（2026-09-15 实测，本机强制）

**本机 `zh.wikipedia.org` / `en.wikipedia.org` / `www.wikidata.org` 直连一律超时**，必须走系统代理：

```
直连   : 超时 74s → WinError 10060 连接尝试失败
走代理 : OK 2.7s  → 正常返回 JSON
```

```powershell
# 调用前必须先设代理（否则 100% 失败）
$env:HTTP_PROXY='http://127.0.0.1:10809'
$env:HTTPS_PROXY='http://127.0.0.1:10809'
python $S summary "人工智能" --lang zh
python $D fact Q312
```

> ⚠️ 这与 firecrawl 的要求不同：firecrawl 因**其 CLI 自身 bug**需 wrapper 内部临时清空代理
> （**不是网络问题**——经代理 curl 实测能到达 firecrawl）。你只需记住：**保持带代理**，
> firecrawl 走 wrapper 即可，两者不冲突。
> 脚本 `s_wikipedia.py` / `s_wikidata.py` 本身不设代理，依赖调用方传入的环境变量。
> 若 `$env:HTTP_PROXY` 已是 `http://127.0.0.1:10809`（本机默认），则无需额外操作。

## ⚠️ 图片文件下载（upload.wikimedia.org）—— 2026-09-26 实测

**本节解决的是"下载条目里的地图/图片二进制文件"，不是文本抓取。** 图片 CDN 与文本 API 的限流策略完全不同，`s_wikipedia.py` 不覆盖此场景。

实测限流对比（共享数据中心代理 IP）：

| 通道 | 结果 |
|------|------|
| Commons API 文本搜索（`list=search`） | ✅ 宽松，几十次都没事 |
| **原图直链** `upload.wikimedia.org/wikipedia/commons/X/XX/File.jpg` | ❌ **约 3–8 张即 HTTP 429**，最狠 |
| wsrv.nl / images.weserv.nl 图片代理转取 | ⚠️ 部分文件 404（缓存不到），且 URL 里已有的 `%xx` 会被二次转义需注意 |
| **`Special:FilePath` + 标准缩略宽度** | ✅ **全部成功**（实测 8/8） |

**正确姿势：走 `Special:FilePath` 重定向 + 1920px 标准宽度**（1920px 是缩略图服务的标准缓存档，命中率最高）：

```powershell
# 文件名可读形式（Special:FilePath 自动处理 URL 编码与重定向）
https://commons.wikimedia.org/wiki/Special:FilePath/<文件名含扩展名>?width=1920

# 实际下载（PS）：
Invoke-WebRequest -Uri 'https://commons.wikimedia.org/wiki/Special:FilePath/Topographic_map_of_the_USA.png?width=1920' `
  -OutFile out.png -Proxy $env:HTTPS_PROXY -UserAgent 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
```

操作纪律：

1. **拿文件名**：先用 Commons API `action=query&list=search&srnamespace=6`（namespace 6 = File:）搜，或从条目 `media-list` 端点取（`/api/rest_v1/page/media-list/{title}`）
2. **下载间隔 ≥10–15 秒**，短间隔重试只会加固封锁；429 后等待 30s+ 再试
3. **UA 别用裸 PowerShell 默认值**，带浏览器形态 UA；务必带代理
4. 429 顽固时的兜底链：`thumb.wikimedia.org/.../1920px-<文件名>` 直链（从 Special:FilePath 重定向后的最终 URL 抄）→ 换出口 IP → 最后才考虑 wsrv.nl
5. 大图（数 MB 的 PNG）下载后**检查文件头**（PNG `89 50 4E 47` / JPEG `FF D8`），429 有时返回错误页而非抛异常，写盘的可能是 HTML

## 快速使用

```powershell
$S = "<skills-path>\agent-reach\scripts\s_wikipedia.py"
$D = "<skills-path>\agent-reach\scripts\s_wikidata.py"

# ===== Wikipedia =====
python $S summary "人工智能" --lang zh     # 摘要（含描述/缩略图/wikidata ID）
python $S page "量子计算机" --lang zh      # 全文纯文本（已剥标签+过滤维护模板）
python $S page "量子计算机" --lang zh --max-chars 2000   # 截断
python $S search "量子计算" --lang zh --limit 10
python $S sections "量子计算机" --lang zh # 分节目录（配合 page 精读）
python $S langs "人工智能" --lang zh      # 跨语言版本（实测 181 个）
python $S random --lang zh --count 3      # 随机条目

# ===== Wikidata（与上面配对）=====
python $D search "苹果" --limit 5         # 实体搜索（消歧首选入口）
python $D batch "Q89,Q312,Q11660"         # 批量标签/描述/别名
python $D fact Q312                       # 人读事实卡片（Q 编号已译成中文标签）
python $D entity Q11660                   # 全量（含 sitelinks/claims）
python $D entity Q11660 --no-claims       # 更快，只要标签/跨语言
python $D sparql --query-file q.rq        # 任意 SPARQL（⚠️ 勿用 --query 传引号，见踩坑 #9）

# 加 --raw 输出紧凑单行 JSON（便于管道/入库）
```

**语言参数**：`--lang zh`（默认）/ `en` / `ja` / `de` / `fr` / `ru` / `simple` 等。zh 和 en 内容差异大，写报告建议 **zh 取本地视角 + en 取全球视角**并用。

## 配合工作流（推荐）

```powershell
# 1. Wikipedia 拿摘要 + Q 编号
python $S summary "人工智能" --lang zh        # → wikidata_id: Q11660
# 2. Wikidata 拿结构化事实 + 跨语言标题
python $D fact Q11660                          # 事实卡片
python $D entity Q11660 --no-claims            # sitelinks: 212 个语言版本
# 3. 用 Q 编号做多语言/多源聚合的去重主键
```

## 实体消歧：`wikidata_id` / Q 编号是什么

维基百科有 300+ 语言版本，**各语言条目页相互独立**，按「标题」认会掉坑。Wikidata 给现实世界每个实体分配唯一编号（Q 编号），**跨语言、跨维基恒定**。

**实测数据**：

| 查询 | Q 编号 | description |
|------|--------|-------------|
| zh 维基「苹果」 | `Q89` | 植物，果实是一种水果 |
| zh 维基「苹果公司」 | `Q312` | 美國的跨國科技公司 |
| **en 维基「Apple Inc.」** | **`Q312`** | ← 与中文「苹果公司」同一实体 |

中文「苹果公司」与英文「Apple Inc.」**标题毫无字面相似**，但 Q 编号都是 `Q312` → 程序可精确判定同一实体。反之「苹果」vs「苹果公司」只差两字，Q 编号却完全不同。

**用途**：跨语言合并同类项、多源去重、歧义检测、结构化事实查询、知识图谱稳定主键。标题会被重命名、URL 会变、各语言标题不同——**Q 编号不会变**，所以建索引/合并时用它当主键。

**消歧流程**：

```powershell
python $D search "苹果"        # 看有几个候选实体
#   Q89     苹果      植物，果实是一种水果
#   Q312    蘋果公司   美國的跨國科技公司      ← aliases 含 "苹果"、"水果店"
#   Q158657 苹果      蔷薇科苹果属的一种植物
#   Q595660 苹果      1998 film by Samira Makhmalbaf
# 多个候选且都合理 → 向用户澄清，别猜；确定后拿 Q 编号去 fact/entity
```

**`search` 的 `aliases` 字段是消歧关键**：`Q312` 别名含「苹果」「水果店」，这解释了为什么搜「苹果」公司会冒出来——是别名匹配，不是错误。

## ⚠️ 踩坑记录（全部本机实测，2026-09）

### 1. `action=query&prop=extracts` 在**中文维基返回空字符串**

```
GET /w/api.php?action=query&prop=extracts&explaintext=1&titles=量子计算
→ {"query":{"pages":{"848861":{"extract":""}}}}          ← zh: 空！
→ en.wikipedia 同参数正常返回 1167 字符                    ← en: 正常
```

**根因**：`TextExtracts` 扩展在 zh.wikipedia 上未启用/被禁用。`explaintext`、`exintro`、`exchars` 各种组合全部返回空串，**不报错**（静默失败，最阴险的一种）。

**结论**：取摘要用 REST `/page/summary`，取正文用 `action=parse&prop=text`。**永远不要用 `prop=extracts`。**

### 2. 正文**不要**用 REST `/page/html`（会混入原始 wikitext）

REST `/page/html/{title}` 会把 infobox / 模块的原始 wikitext 以 JSON 形式内嵌在 HTML 里，剥完标签后残渣污染正文：

| 端点 | en 体积 | zh 体积 | `{"wt":` 残留 |
|------|--------:|--------:|--------------:|
| REST `/page/html` | 864 KB | 757 KB | **1425 处 / 734 处** ❌ |
| `action=parse&prop=text` | 512 KB | 238 KB | **0 处 / 0 处** ✅ |

`action=parse&prop=text` 体积还接近减半。**正文一律走它。**

代价：`parse` 不返回 `<section>` 结构 → 分节目录（`sections`）仍单独走 REST `/page/html`（它的 `<section>` 标签是现成的）。

### 3. `action=parse` 遇重定向只返回重定向符

```
GET /w/api.php?action=parse&page=量子计算&prop=wikitext
→ 只返回 '#REDIRECT [[量子计算机]]'（约 58 字节）
```

**必须带 `redirects=1`**，脚本已默认加上（跟随重定向后正常返回 "AI"→"Artificial intelligence" 全文）。

### 4. 限流阈值低，匿名连续约 10 次即被拦

```
You are making too many requests to the API.
```

触发后**整个 IP 段短暂封锁**（连正常的 summary 请求也被拒）。触发时间点约在连续 10 次快速请求后。

**对策（脚本内已实现）**：
- 请求间强制间隔 `MIN_INTERVAL=0.8s`（环境变量 `WIKI_MIN_INTERVAL` / `WD_MIN_INTERVAL` 可调）
- 真实 UA（含联系方式）
- 失败指数退避重试 3 次（1.5s → 3s → 6s）
- 识别 "too many requests" 文本 → 抛 `RATE_LIMITED`（退出码 3）

**批量抓取**：一次任务别超过约 50 个条目，分批次 + 间隔。需要大批量时考虑 [dumps](https://dumps.wikimedia.org/) 离线库，别硬刷 API。

### 5. 消歧义页要识别

`summary` 的 `type` 字段：`standard`（正常）/ `disambiguation`（消歧义）。消歧义页的 `extract` 是一串候选列表，**不是条目内容**，脚本会在 `note` 字段提示。遇到时需向用户澄清具体所指。

实测：`"AI"` → `type=disambiguation`（列出人工智能/人工授精/Adobe Illustrator…）；`"苹果"` → `type=standard`（植物，`description="植物，果实是一种水果"`）。

### 6. 中英文页的维护模板

zh 页面首页常有大量「本條目存在以下問題…需要編修/補充來源/翻譯品質不佳」维护框，API 返回里体积很大。脚本的 `_strip_html(drop_hatnotes=True)` 已默认整块丢弃，直接进正文。

### 7. `wbgetentities` 的 `props` 必须显式列全

```
action=wbgetentities&ids=Q89&props=labels|descriptions
→ 只返回 labels 和 descriptions，aliases/sitelinks/claims 一律没有
```

**不是"默认全给"**。要 aliases 就必须写进 props。不想操心就用 `Special:EntityData/{Q}.json`（一次给全）。

### 8. SPARQL 变量未绑定 → 静默返回空结果（不报错）

```
SELECT ?neverBound WHERE { wd:Q312 wdt:P112 ?val . } LIMIT 2
→ {"bindings":[{"neverBound": null}, ...]}     ← 不报错，只是全空
```

SELECT 里的变量必须在 WHERE 中真实绑定。写错变量名不会得到错误提示，只得到**一堆空行**——很容易误判成「这个实体没有该属性」。

脚本已加检测：所有行都为空时返回 `warning` 字段提示。

### 9. 命令行传含双引号的 SPARQL 必被剥引号

label service 的 `bd:serviceParam wikibase:language "zh,en"` 含双引号。经 PowerShell/argparse 传参时引号被剥掉：

```
收到: ... wikibase:language zh,en.      ← 引号没了
服务端: 400 BAD_REQUEST (java.util.concurrent.ExecutionException)
```

**这不是 PowerShell 独有**——实测用 `Get-Content -Raw` 读文件再传 `--query` 也会被剥。**唯一可靠方式是 `--query-file`**：

```powershell
# ✅ 正确：写文件再读
@'
SELECT ?valLabel WHERE {
  wd:Q312 wdt:P112 ?val .
  SERVICE wikibase:label { bd:serviceParam wikibase:language "zh,en". }
} LIMIT 3
'@ | Set-Content -Encoding UTF8 q.rq
python $D sparql --query-file q.rq
```

**BOM 陷阱**：PowerShell 的 `Set-Content -Encoding UTF8`（PS 5.1）会写 UTF-8 BOM，SPARQL 解析器遇到 BOM 直接 400。脚本已用 `utf-8-sig` 读取自动吃掉。用 `-Encoding utf8NoBOM` 或 `[IO.File]::WriteAllText` 也可规避。

### 10. SPARQL 无 LIMIT 会返回海量行

```
SELECT ?x WHERE { wd:Q42 ?p ?x }        ← 无 LIMIT
→ 972 行，大量是 statement URI（Q42-44889d0f-474c-...）、多语言 aliases
```

脚本已防护：检测到无 `LIMIT` 自动追加 `LIMIT 200`，并在 `note` 里告知。要更多就自己写明 LIMIT。

### 11. SPARQL 无预告式限流头

不像 Wikipedia REST 有 `ETag`/`x-ratelimit-*`，SPARQL 端点**不返回限流预告头**，超限时直接 429 或 `Query timeout`。只能靠 429 重试 + 语义化查询兜底。查询超时 60s 硬上限。

### 12. `fact` 的引用值是 Q 编号，需二次解析

`P112`（创始人）的值是 `Q483382` 这种编号，直接输出对用户无意义。**脚本已自动解析**成 `史蒂夫·沃兹尼亚克`（并附 `value_label_all` 给出中英对照）。

实测 Q312 输出：

| 属性 | 值 |
|------|-----|
| 创始人 | 史蒂夫·沃兹尼亚克 |
| 总部 | 庫比蒂諾 |
| 国家 | 美國 |
| 成立时间 | 1976-04-01 |
| CEO | 麥克·史考特 |
| 官网 | https://apple.com/at/ |

> 注：`P169`(CEO) 和 `P856`(官网) 的 `claim_count` 分别是 8 和 109，说明**多值属性**。脚本默认取 `mainsnak`（主值），要全量值需读 `claims`。

## 端点速查表

### Wikipedia

| 用途 | 端点 | 关键参数 |
|------|------|---------|
| 摘要+元信息 | `GET /api/rest_v1/page/summary/{title}` | title 需 URL 编码 |
| 正文 HTML | `GET /w/api.php?action=parse&prop=text&page={t}&redirects=1` | 取 `parse.text["*"]` |
| 全文搜索 | `GET /w/api.php?action=query&list=search&srsearch={q}` | `srlimit`(≤500)、`srprop=snippet` |
| 分节结构 | `GET /api/rest_v1/page/html/{title}` | 解析 `<section data-mw-section-id>` |
| 跨语言 | `GET /w/api.php?action=query&prop=langlinks&titles={t}` | `lllimit`(≤500) |
| 随机条目 | `GET /w/api.php?action=query&generator=random&grnnamespace=0` | `grnlimit`(≤10) |
| 分类成员 | `GET /w/api.php?action=query&list=categorymembers&cmtitle=Category:{c}` | `cmlimit`(≤500) |
| ❌ 禁用 | `action=query&prop=extracts` | **zh 返回空串，勿用** |

**其他有用的 prop**（同样走 `action=query`）：
- `prop=revisions&rvprop=content` — 原始 wikitext
- `prop=categories` — 所属分类
- `prop=links` / `prop=backlinks` — 外链/反链
- `list=search&srwhat=text` — 全文检索（默认）；`srwhat=title` 仅搜标题
- `list=geosearch` — 按地理坐标找条目

### Wikidata

| 用途 | 端点 | 关键参数 |
|------|------|---------|
| 实体全量 | `GET /wiki/Special:EntityData/{Q}.json` | 一次给全（含 aliases） |
| 批量实体 | `GET /w/api.php?action=wbgetentities&ids=Q89\|Q312` | **props 必须显式列全** |
| 实体搜索 | `GET /w/api.php?action=wbsearchentities&search={q}&language=zh` | `uselang`、`type=item` |
| SPARQL | `GET query.wikidata.org/sparql?query={q}&format=json` | 带 LIMIT；Accept: `application/sparql-results+json` |
| 实体 URI | `http://www.wikidata.org/entity/Q312` | RDF 命名空间 |

**常用属性 ID**（脚本 `PROP_LABELS` 内置翻译）：

| 属性 | 含义 | 属性 | 含义 |
|------|------|------|------|
| P31 | 是…的实例 | P569 | 出生日期 |
| P279 | 上级分类 | P570 | 逝世日期 |
| P361 | 隶属于 | P19 | 出生地 |
| P571 | 成立时间 | P27 | 国籍 |
| P159 | 总部 | P106 | 职业 |
| P17 | 国家 | P50 | 作者 |
| P112 | 创始人 | P57 | 导演 |
| P127 | 所有者 | P136 | 类型/流派 |
| P169 | 首席执行官 | P277 | 编程语言 |
| P856 | 官网 | P348 | 软件版本 |

## SPARQL 实用模板

```sparql
-- 某实体的所有「创始人」（label service 输出中文）
SELECT ?founderLabel WHERE {
  wd:Q312 wdt:P112 ?founder .
  SERVICE wikibase:label { bd:serviceParam wikibase:language "zh,en". }
} LIMIT 5

-- 反向查：谁把某实体当作实例（找同类）
SELECT ?item ?itemLabel WHERE {
  ?item wdt:P31 wd:Q5 .            -- 是人类
  ?item wdt:P106 wd:Q82594 .       -- 职业是程序员
  SERVICE wikibase:label { bd:serviceParam wikibase:language "zh,en". }
} LIMIT 10

-- 按属性存在性筛选（找有官网的公司）
SELECT ?item ?itemLabel ?site WHERE {
  ?item wdt:P31 wd:Q6881511 .      -- 是工商企业
  ?item wdt:P856 ?site .
  SERVICE wikibase:label { bd:serviceParam wikibase:language "zh,en". }
} LIMIT 10
```

## REST 与 Action API 的选型原则

```
要摘要 / 单条元信息     → REST /page/summary     （最省事）
要正文纯文本            → Action parse&prop=text （别用 REST html）
要搜索 / 列表 / 跨语言  → Action query&list/prop （REST 没有这些）
要 <section> 分节结构   → REST /page/html        （parse 没有）
要结构化事实 / 实体编号  → Wikidata fact / entity
要复杂关系查询          → Wikidata SPARQL
```

## 可用的 REST 端点补充

`/api/rest_v1/` 下还有（均免密钥）：

| 端点 | 用途 |
|------|------|
| `/page/summary/{title}` | 摘要（首选） |
| `/page/html/{title}` | 渲染后 HTML（含 section 结构；正文勿直接用） |
| `/page/related/{title}` | 相关条目推荐 |
| `/page/random/{format}` | 随机条目（`/page/random/summary` 直接给 JSON） |
| `/page/media-list/{title}` | 条目内所有图片/媒体 |
| `/page/title/{title}` | 标题规范化 |
| `/page/mobile-sections/{title}` | 移动版分节结构（更细） |
| `/page/segments/{title}` | 首段摘要（比 summary 更短） |
| `/feed/featured/{yyyy}/{mm}/{dd}` | 当日特色内容 |

`/api/rest_v1/` 支持 `Accept: application/json`，且响应带 `ETag`（可做条件请求省流量）。

## 与 Firecrawl / Jina 的关系

Wikipedia 页面**结构极规整、无登录墙、无 JS 反爬**，官方 API 是绝对首选：

| 方式 | 何时用 |
|------|--------|
| **官方 API**（本渠道） | ✅ 默认。结构化、快、免费、免密钥 |
| Firecrawl scrape | 仅当需要**渲染后带样式的完整页面**（如要保留表格/公式排版） |
| Jina Reader | 不需要，API 已更干净 |

不要用 `curl` 裸抓 `zh.wikipedia.org/wiki/xxx` HTML——那是未渲染版本，正文里混着 wikitext，比 API 差。

## 状态

| 项 | Wikipedia | Wikidata |
|----|-----------|----------|
| 凭证 | **无需**（零配置） | **无需**（零配置） |
| 依赖 | 仅 Python 标准库 | 仅 Python 标准库 |
| 脚本 | `scripts/s_wikipedia.py` | `scripts/s_wikidata.py` |
| 动作 | summary/page/search/sections/langs/random | search/batch/fact/entity/sparql |
| 实测语言 | zh ✅ / en ✅ / ja ✅ | zh ✅ / en ✅ |
| 限流 | 匿名约 0.8s/次；内置节流+退避 | 同左；SPARQL 无预告头 |
| 实测日期 | 2026-09-14 | 2026-09-14 |

## 用例建议

- **事实核查 / 背景补充**：`summary` 拿 `description`+`extract`+`wikidata_id` 就够写一段背景
- **深度调研**：`sections` 看结构 → `page` 取全文 → 按需读特定段落
- **多语言对照**：`langs` 找目标语言标题 → 对应 lang 再 `summary`/`page`
- **实体消歧**：`search` 看 description/aliases → 澄清或选定 Q 编号
- **事实卡片**：`fact Q...` 直接得到人读属性表（已译中文）
- **跨语言去重**：`batch` 比对 Q 编号判定「中英两条资料是否同一实体」
- **复杂关系**：`sparql` 查「子公司/创始人/所属分类」等正文没有的结构化关系
- **知识图谱锚点**：Q 编号作为稳定主键对接下游
