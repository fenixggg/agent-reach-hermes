---
name: agent-reach
description: >
  MUST USE when user asks to search, browse, read, or interact with content from any of these platforms:
  微信公众号/微信/wechat, 小红书/xiaohongshu/xhs, Twitter/推特/X, B站/bilibili/哔哩哔哩,
  V2EX, Reddit, LinkedIn/领英, YouTube, GitHub code search,
  小宇宙播客, 雪球/股票行情, 微博/weibo/热搜, RSS feeds, 豆瓣/douban（电影/影评/短评）,
  今日头条/toutiao/头条/微头条, 维基百科/wikipedia/百科, Wikidata/wikidata/Q编号/实体消歧, Quora/Quora问答/Quora回答, or any web URL.

  Also MUST USE for: web搜索/搜/查/找/look up/research, 招聘/求职/jobs, 分享的链接/URL.
  Routes to CLI tools: wechat_search.py, s_wechat_article.py, zhihu-cli, snowball-cli, xhs-cli, twitter-cli, bili, rdt-cli, gh, yt-dlp, tw_run.py, s_toutiao.py, s_wikipedia.py, s_wikidata.py, s_quora.py.
  17 platforms (维基百科+Wikidata 合为一个渠道). 严格零配置渠道 5 个（微信/头条/V2EX/豆瓣/维基+Wikidata），其余部分命令免登录（weibo 热搜、bili 读命令、snowball 行情）或消耗积分（Quora 走 Firecrawl，1积分/次）。career/LinkedIn 当前为死渠道。

  【路由方式】SKILL.md 包含路由表和常用命令，复杂场景需按需阅读对应分类的 references/*.md。
  分类：search / 国内平台(微信/知乎/雪球/微博/ B站/小红书/豆瓣/V2EX/头条) / 国外平台(Twitter/Reddit/YouTube/维基百科+Wikidata/Quora/GitHub) / web / career(LinkedIn)。
triggers:
  - search: 搜/查/找/search/搜索/查一下/帮我搜
  - wechat: 微信/公众号/微信文章/搜微信/查公众号/wechat
  - social:
    - 小红书: xiaohongshu/xhs/小红书/红书
    - Twitter: twitter/推特/x.com/推文
    - B站: bilibili/b站/哔哩哔哩
    - 微博: weibo/微博/热搜
    - V2EX: v2ex
    - Reddit: reddit
    - 豆瓣: douban/豆瓣/影评/豆瓣评分/豆瓣短评/电影评分
    - 今日头条: toutiao/头条/今日头条/微头条
  - quora: quora/Quora问答/Quora回答/quora.com
  - career: 招聘/职位/求职/linkedin/领英/找工作
  - github: github/代码/仓库/gh/issue/pr/分支/commit
  - web: 网页/链接/文章/rss/读一下/打开这个
  - wiki: 维基百科/wikipedia/wiki/百科/词条/条目录/百科条目
  - wikidata: wikidata/Q编号/实体消歧/结构化事实/跨语言链接
  - video: youtube/视频/播客/字幕/小宇宙/转录/yt/文字稿/转文字/音频转写
  - transcribe: 转录/转文字/文字稿/字幕/语音转文字/音频转文字/视频转文字
  - finance: 雪球/股票/stock/xueqiu/行情/基金/雪球帖子/大V观点
---

# Agent Reach — 路由器

**17 渠道工具集合**（16 个平台 + 搜索/网页/GitHub/招聘等通用工具；维基百科与 Wikidata 合为一个渠道）。
根据用户意图选择对应分类。

## 路由表（第一层直达，社交平台按国内/国外分列，按使用频率排序）

### 国内平台

| 用户意图 | 平台 | 详细文档 |
|---------|------|---------|
| 微信公众号文章搜索 | wechat | [references/wechat.md](references/wechat.md) |
| 微信公众号文章**正文提取** | wechat | `scripts/s_wechat_article.py`（curl_cffi 指纹伪装；微信直链勿用 better-webfetch，2026-10-03 实测已失效） |
| 知乎 搜索/热榜/直答 | zhihu | [references/zhihu.md](references/zhihu.md)（社区版 pyzhihu-cli；另有官方 zhihu-cli.exe，见文档） |
| 雪球 帖子/讨论/大V观点 | xueqiu | [references/xueqiu.md](references/xueqiu.md)（snowball-cli） |
| 微博 热搜/搜索/评论/大V | weibo | [references/weibo.md](references/weibo.md)（weibo-cli + 搜索脚本） |
| Bilibili/哔哩哔哩/B站 | bili | [references/bilibili.md](references/bilibili.md)（**下载视频走 yt-dlp，见 video.md**） |
| 小红书 | xhs | [references/xiaohongshu.md](references/xiaohongshu.md) |
| 豆瓣（电影/影评/短评） | douban | [references/douban.md](references/douban.md) |
| V2EX | v2ex | [references/v2ex.md](references/v2ex.md)（公开API） |
| 今日头条 文字内容（搜索/正文/评论/热榜） | toutiao | [references/toutiao.md](references/toutiao.md)（s_toutiao.py，免登录；**视频不支持**） |

### 国外平台

| 用户意图 | 平台 | 详细文档 |
|---------|------|---------|
| Twitter/X | twitter | [references/twitter.md](references/twitter.md)（**必须走 `scripts/tw_run.py`**） |
| Reddit | reddit | [references/reddit.md](references/reddit.md) |
| YouTube/播客字幕 + **B站/YouTube 视频下载** | video | [references/video.md](references/video.md)（✅ YouTube 2026-10-02 恢复可用） |
| 维基百科/百科/词条/Wikidata/Q编号/实体消歧/结构化事实 | wikipedia | [references/wikipedia.md](references/wikipedia.md)（Wikipedia + Wikidata 双渠道，官方 API，免密钥） |
| Quora 问答提取（答案页/问题页） | quora | [references/quora.md](references/quora.md)（`scripts/s_quora.py`，Firecrawl 渲染，**每次1积分**；零HTTP路线已实测全灭勿再试） |
| GitHub/代码 | github | [references/github.md](references/github.md) |

### 通用工具（不分国内外）

| 用户意图 | 分类 | 详细文档 |
|---------|------|---------|
| 网页搜索/代码搜索 | search | [references/search.md](references/search.md) |
| 网页/文章/RSS | web | [references/web.md](references/web.md) |
| 招聘/职位/LinkedIn | career | [references/career.md](references/career.md)（⚠️ 死渠道：LinkedIn 本机无可用通道，仅 Tavily 搜索公开摘要兜底） |

> 旧 `social.md` 已拆分为上述各平台独立文档，按行直达，不再需要先读 social 总览。

## 搜索路由优先级（用户偏好，2026-10-02 对齐全局纪律）

当用户要求"查/搜/找"时，按以下优先级选择工具：

| 优先级 | 场景 | 工具 | 说明 |
|:------:|------|------|------|
| 1 🥇 | **信息查询**（无具体URL） | **10r_search**（engine=combo）→ Tavily → Exa | Desktop 会话插件不注入时用 CLI：`python "E:\AI Output\Hermes-Workspace\scripts\10r_cli.py" search "query"`。**搜索绝不用 Firecrawl** |
| 2 🥇 | **社媒/平台内容**（agent-reach 覆盖，自媒体难爬） | **Agent-Reach 对应平台通道**（本 skill） | 每个平台有专用 CLI/脚本，比通用抓取稳 |
| 3 🥇 | **其它通用静态网页** | **better-webfetch** → 10r_fetch → firecrawl（兜底） | 免费最快（~0.3-1.6s）；Desktop 会话 fetch 用 `10r_cli.py fetch`，`--save-to` 可落盘 |
| 4 🥈 | **读复杂页面**（JS渲染/需登录/需交互） | **Firecrawl**（`--wait-for` / `--proxy basic`） | 完整浏览器渲染，走 wrapper |
| 5 🚨 | **页面变化监控** | **Firecrawl monitor** | 定时检查，webhook通知 |

**原则：** 10r_search 搜信息 → 社媒走 Agent-Reach 平台通道 → 静态页 better-webfetch（10r_fetch 次之、firecrawl 兜底）。

> ⚠️ **firecrawl 只做抓取，禁止用其 search**（用户 2026-07-22 纪律）。
> ⚠️ **代理保持开启**（墙外站/Wikipedia/Twitter 都需要）。firecrawl 因**其 CLI 自身 bug**
> 需走 wrapper（内部临时清空代理绕开）——**不是网络不通**，经代理实测能到达 firecrawl。
> ⚠️ **Desktop 会话注意**：source=desktop 的会话拿不到 10r_search/10r_fetch 等插件工具（CLI/网关正常），
> 一律用 `E:\AI Output\Hermes-Workspace\scripts\10r_cli.py` 替代（纯标准库，fetch 支持 --save-to）。
> 完整路由见 [references/web.md](references/web.md)。

## 零配置快速命令

```bash
# 微信公众号搜索与直链解析 (解密真实 mp.weixin.qq.com 链接)
python <skill-path>/scripts/wechat_search.py "关键词" --limit 5

# 微信文章正文提取 (2026-10-03 实测: better-webfetch 对搜狗签名直链已失效——微信升级为 TLS 指纹风控,
#   httpx 拿到的是拦截页。本脚本用 curl_cffi 伪装 Chrome 指纹抓正文+图片,免 cookie 免登录,~1s)
python <skill-path>/scripts/s_wechat_article.py "微信直链URL"                # JSON 信封(bwf 兼容)
python <skill-path>/scripts/s_wechat_article.py "微信直链URL" --format md    # 纯 Markdown

# 通用网页阅读 (Firecrawl — 首选；⚠️ 必须走 wrapper：它自动清代理 + 加载 key)
#   Hermes 侧:
#   bash <skills-path>/firecrawl-cli/scripts/firecrawl.sh "URL" --only-main-content
#   （裸调 PATH 里的 firecrawl 会因代理 bug 把 URL 误拼进路径 → 恒定 404）
bash <firecrawl-cli>/scripts/firecrawl.sh "URL" --only-main-content

# GitHub 搜索
gh search repos "query" --sort stars --limit 10

# Twitter 搜索（⚠️ 必须走 tw_run.py 包装器：强制用户级 VPN 代理，绕过 Agent 注入的无效代理）
python <skill-path>/scripts/tw_run.py search "query" -n 10 --json
python <skill-path>/scripts/tw_run.py user-posts @sama -n 20 --yaml
python <skill-path>/scripts/tw_run.py feed -n 20 --json

# X 当日热点扫描（多主题并行采集 + 互动量排序 + 去重；X 无趋势榜接口，只能用此法）
python <skill-path>/scripts/x_hot_topics.py --hours 24 --top 40

# B站视频详情
bili video BVxxx --yaml

# B站字幕
bili video BVxxx --subtitle

# ⭐ B站 下载视频/音频（⚠️ 要求 yt-dlp ≥ 2026.07.04，旧版恒 412｜`yt-dlp -U` 升级）
yt-dlp -f "bv*+ba/b" --merge-output-format mp4 "https://www.bilibili.com/video/BVxxx"
yt-dlp -f "ba/b" -x --audio-format m4a "URL"        # 仅音频
yt-dlp -F "URL"                                      # 先侦察可用画质
# ⚠️ 不要用 `bili audio` —— 会卡死无产物

# 字幕下载 (yt-dlp)
yt-dlp --write-sub --write-auto-sub --sub-lang "zh-Hans,zh,en" --convert-subs srt --skip-download "URL"

# ✅ YouTube：2026-10-02 实测恢复可用（格式侦察 RC=0 含 4K）
#    ⚠️ 真实下载前建议先 -F 侦察确认，详见 references/video.md

# Reddit 搜索
rdt search "query" --limit 10

# Reddit 读帖 + 评论
rdt read POST_ID

# V2EX 热门
curl -s "https://www.v2ex.com/api/topics/hot.json" -H "User-Agent: agent-reach/1.0"

# 小红书搜索
xhs search "query"

# 小红书读笔记
xhs read NOTE_ID_OR_URL

# 小红书读评论（必须带 xsec_token 的完整URL；--all 自动翻页）
# ⚠️ 若报 {code:-1}/HTTP 406：升级依赖 python -m pip install --upgrade xhshow（非 pipx upgrade）
xhs comments NOTE_ID_OR_URL --json
xhs comments NOTE_ID_OR_URL --all --json

# 视频转录（B站/YouTube/小红书/通用）
python <skill-path>/scripts/transcribe.py "URL" [输出目录]

# 今日头条文字内容（免登录、免凭证、无硬性频率限制）
# ⚠️ 仅文字内容：图文/微头条/评论/热榜。视频抓取技术不可行，已放弃。
python <skill-path>/scripts/s_toutiao.py search "关键词" --limit 10
python <skill-path>/scripts/s_toutiao.py search "关键词" --type weitoutiao   # 微头条
python <skill-path>/scripts/s_toutiao.py search "关键词" --type all          # 图文+微头条

# 今日头条读正文（自动判别 文章/微头条）+ 评论
python <skill-path>/scripts/s_toutiao.py read <gid或URL> --comments 20

# 今日头条热榜
python <skill-path>/scripts/s_toutiao.py hot --limit 50

# 维基百科（官方 API，免密钥、免登录、零配置）
python <skill-path>/scripts/s_wikipedia.py summary "人工智能" --lang zh   # 摘要+元信息
python <skill-path>/scripts/s_wikipedia.py page "量子计算机" --lang zh     # 全文纯文本
python <skill-path>/scripts/s_wikipedia.py search "量子计算" --lang zh --limit 10
python <skill-path>/scripts/s_wikipedia.py sections "量子计算机" --lang zh # 分节目录
python <skill-path>/scripts/s_wikipedia.py langs "人工智能" --lang zh      # 跨语言
# ⚠️ 勿用 action=query&prop=extracts —— zh.wikipedia 返回空串（静默失败）
# ⚠️ 正文勿用 REST /page/html —— 会混入 1425 处原始 wikitext 残渣

# Quora 问答提取（Firecrawl 渲染 + 本地答案切割；每次烧1积分，其它站点勿用）
python <skill-path>/scripts/s_quora.py "https://www.quora.com/<Q-slug>/answer/<user>"           # 答案页,最干净
python <skill-path>/scripts/s_quora.py "https://www.quora.com/<Q-slug>" --limit 5               # 问题页多答案
python <skill-path>/scripts/s_quora.py "URL" --format md

# Wikidata（官方 API + SPARQL，免密钥）—— 与 Wikipedia 配对使用
python <skill-path>/scripts/s_wikidata.py search "苹果" --limit 5      # 实体搜索（消歧）
python <skill-path>/scripts/s_wikidata.py batch "Q89,Q312"            # 批量标签/别名
python <skill-path>/scripts/s_wikidata.py fact Q312                   # 人读事实卡片
python <skill-path>/scripts/s_wikidata.py entity Q11660 --no-claims   # 全量+跨语言
python <skill-path>/scripts/s_wikidata.py sparql --query-file q.rq    # SPARQL（勿用 --query 传引号）
```

**Wikipedia + Wikidata 配合**：`summary` 返回的 `wikibase_item` 就是 Q 编号 → 喂给 `s_wikidata.py` 取结构化事实与跨语言链接。Q 编号跨语言恒定，是实体消歧/多源去重的稳定主键。

## 环境检查

```bash
# 检查可用 CLI 工具
where xhs twitter bili rdt gh yt-dlp python 2>nul
# ⚠️ xhs/twitter 等是 uv tool 安装，pip list 查不到；用 uv tool list 查：
uv tool list
```

## 工作区规则

不要在 agent workspace 创建文件。使用 `%TEMP%` 存放临时输出，`~/.agent-reach/` 存放持久数据。

## ⚠️ 代理规则（2026-09-15 实测校正）

环境变量 `HTTP_PROXY` / `HTTPS_PROXY` **已设为 `http://127.0.0.1:10809`**。
**总体原则：保持带代理。** 只有 firecrawl 因其 CLI 自身 bug 需要 wrapper 内部临时清空。

| 通道 | 代理要求 | 做法 |
|------|---------|------|
| **Wikipedia / Wikidata** | **必须带代理** | 直连超时 74s；带代理 2.7s。见 references/wikipedia.md |
| **Twitter/X** | **必须带代理** | 走 `scripts/tw_run.py`（自动从注册表读真代理） |
| 其他墙外站（GitHub 等） | **必须带代理** | 保持 `$env:HTTP_PROXY='http://127.0.0.1:10809'` |
| **firecrawl**（通用网页抓取） | **走 wrapper**（内部临时清代理） | 绕开 CLI 的 URL 拼装 bug。**勿裸调**，详见 references/web.md |

> ⚠️ firecrawl 的清代理**不是"网络到不了国外"**——经代理 curl 实测能正常到达 firecrawl。
> 是 CLI 把目标 URL 误当"路径"发给了本地代理。判别指纹：`--status` 正常但 `scrape` 恒定 404。

## 详细文档

根据用户需求，阅读对应的详细文档：

- [知乎](references/zhihu.md) — 官方 Zhihu CLI：搜索/热榜/直答/额度
- [雪球](references/xueqiu.md) — snowball-cli：股票基金数据查询 + 帖子讨论/KOL观点（行情兜底走东财API）
- [微博](references/weibo.md) — weibo-cli（热搜/详情/评论/用户）+ s_weibo_search.py（关键词搜索）
- [小红书](references/xiaohongshu.md) — xhs-cli
- [Twitter/X](references/twitter.md) — twitter-cli + `scripts/tw_run.py` 代理包装器 + `scripts/patch_twitter_search_post.py` POST 补丁 + `scripts/x_hot_topics.py` 当日热点扫描
- [B站](references/bilibili.md) — bilibili-cli
- [V2EX](references/v2ex.md) — 公开 API
- [Reddit](references/reddit.md) — rdt-cli
- [豆瓣抓取](references/douban.md) — 电影/影评/短评，rexxar 移动版 API（免登录免验证码）
- [今日头条](references/toutiao.md) — s_toutiao.py：**文字内容**专精——搜索/文章正文/微头条/评论/热榜，免登录免签名（移动版 SSR 解析）；⚠️ **视频不可抓**
- [职场招聘](references/career.md) — LinkedIn
- [维基百科 + Wikidata](references/wikipedia.md) — **官方 API，免密钥零配置**。Wikipedia：摘要/全文/搜索/分节/跨语言；Wikidata：Q 编号实体消歧/结构化事实/SPARQL。⚠️ zh 禁用 prop=extracts、正文走 parse&prop=text、SPARQL 引号须走 --query-file
- [Quora 问答](references/quora.md) — s_quora.py：**Firecrawl 渲染 + 本地答案切割**。答案页/问题页双形态，输出 author/凭据/upvotes/text/images 结构化 JSON。**每次 1 积分，Quora 专用**；零 HTTP 路线（curl_cffi/RSS/embed/GraphQL/Quetre）已 2026-10-03 实测全灭，勿再试错
- [GitHub](references/github.md) — GitHub CLI（gh）：仓库/代码/issue 搜索
- [网页阅读](references/web.md) — **通用取数路由唯一源**：Firecrawl 首选、搜索 fallback 链、代理规则、RSS
- [网页工具速查](references/web-tools.md) — 搜索 vs 读取，一页速查
- [视频转录](references/video.md) — YouTube / B站 / 小红书视频 / 小宇宙播客，字幕与转录
- [转录格式规范](scripts/transcribe_format.md) — 转录文字稿格式化规则
- [X/Twitter 获取路径对比](references/x-comparison.md) — twitter-cli (免费) vs x_search (付费稳定+AI总结)
- [微信正文 curl_cffi 兜底配方](references/wechat-curl-cffi.md) — 症状判别（httpx 拦截页 vs curl_cffi 完整页）、指纹池轮换、解析要点、NewsCrawler 移植参考

## 配置渠道

各平台登录凭证（cookie/Access Secret）的存放位置、当前状态和恢复流程，统一记录在对应平台的 references/*.md 的「凭证存放位置」章节。新增平台或凭证失效时，先读对应 md。

**凭证失效巡检（2026-10-03 落地）**：`python <skill-path>/scripts/check_creds.py --yaml` 一键判活全部 PATH 型凭证（B站/知乎/雪球联网判活，xhs/微博/Twitter 因架构限制仅本地检查或转实调链路，详见脚本头注释）。退出码 0=全有效，1=存在失效——可直接挂 cron 每日巡检。

**B站凭证失效恢复（2026-10-03 落地，纯 API 零浏览器）**：`python <skill-path>/scripts/bili_qr_login.py` —— 终端 ASCII + PNG 双二维码 → 手机扫码确认 → 自动备份旧凭证（`.bak-时间戳`）→ 写入 credential.json → nav 终验。当日实战：首次 cookie 死亡恢复全程 <2 分钟，扫码即愈。

**批量抓取降频纪律（CrawlerTutorial 02/08 章沉淀，预防优于处理）**：`requests_per_minute < 30`、页间 `random.uniform(2.0, 5.0)s` 随机延迟、遇 403/412/429 立即换出口不重试同 IP。批量任务（翻页/多账号扫描/热点采集）必须遵守。