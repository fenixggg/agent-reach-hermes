# 网页阅读

> **本文档是「通用网页取数」的唯一路由源。** 其它文档（web-tools.md / SKILL.md 等）如有冲突以本文为准。
> 最后修订：2026-10-02 ｜ 改动：搜索/Fetch 链对齐全局纪律（10r_search 主力、10r_fetch 补层、firecrawl 降为兜底）

## 推荐工作流

| 场景 | 工具 | 优先级 |
|------|------|:------:|
| 搜索信息（无URL） | **10r_search**（engine=combo）→ Tavily → Exa | 🥇 |
| **agent-reach 覆盖的社媒/平台**（自媒体，难爬） | **Agent-Reach 平台通道**（本 skill 各平台 CLI/脚本） | 🥇 |
| 其它通用静态网页（博客/新闻/公众号） | **better-webfetch** → 10r_fetch | 🥇 |
| JS 渲染 / 反爬 / 需登录 | **Firecrawl scrape**（`--wait-for` / `--proxy basic`，兜底） | 🥈 |
| 页面变化监控 | **Firecrawl monitor** | 4 |

**路由原则**（2026-10-02 对齐全局纪律）：
- **搜索**一律 10r_search（engine=combo）→ Tavily → Exa。Desktop 会话插件不注入时用 CLI：
  `python "E:\AI Output\Hermes-Workspace\scripts\10r_cli.py" search "query"`。
- **社媒/自媒体平台**（微信、知乎、雪球、小红书、微博、抖音等）优先走 agent-reach 的**平台专用通道**
  （每个平台有专用 CLI/脚本，比通用抓取稳）；Firecrawl 只在平台通道全灭时兜底（真实浏览器渲染 + 代理池）。
- **静态网页 Fetch 链**：better-webfetch（免费最快 ~0.3-1.6s）→ 10r_fetch（Desktop 会话用 `10r_cli.py fetch`，
  支持 `--save-to` 落盘）→ firecrawl（**兜底**，烧 credits，只在前面全失败时用）。
- Firecrawl 消耗 credits（1000/周期），降级为最后兜底，尽量少用。

## ⚠️ 代理规则（必读，2026-09-15 实测校正）

本机 `HTTP_PROXY` / `HTTPS_PROXY` **环境变量已设为 `http://127.0.0.1:10809`**（系统代理开着）。

**总体原则：保持带代理。** 只有 firecrawl 因**其自身 CLI 的 bug**需要 wrapper 内部临时清空。

| 工具 | 代理要求 | 说明 |
|------|---------|------|
| **Wikipedia / Wikidata** | **必须带代理** | 直连超时 74s；带代理 2.7s 正常 |
| **Twitter/X** | **必须带代理** | 用 `tw_run.py`（自动从注册表读真代理） |
| **墙外站**（better-webfetch 抓 GitHub 等） | **必须带代理** | 直连超时；带代理 200 |
| **firecrawl** | **走 wrapper**（内部临时清代理） | ⚠️ **不是网络问题**，见下方说明。**勿裸调** |

```powershell
# 保持带代理（默认状态，墙外站通用）
$env:HTTP_PROXY='http://127.0.0.1:10809'; $env:HTTPS_PROXY='http://127.0.0.1:10809'
```

### 🔍 为什么 firecrawl 要 special-case（2026-09-15 根因实测）

**常见误解**："firecrawl 是国外服务，代理到不了" / "firecrawl 必须直连外网"。
**实测结论：都不对。代理本身完全没问题。**

| 剥离实验（绕过 CLI，只测网络层） | 结果 |
|---|---|
| `curl` 直连 `api.firecrawl.dev` | **405** ✅ 通（405=方法不允许，说明请求到达了服务器） |
| `curl -x http://127.0.0.1:10809` 到 firecrawl | **405** ✅ **经代理也能到达** |

**真实机制**：firecrawl-cli v1.23.3 的 axios 在读到 `HTTP_PROXY` 时**组装 URL 出错**——
把目标地址当成"路径"发给本地代理，请求**根本没到 firecrawl**：

```
应为: POST https://api.firecrawl.dev/v2/scrape
实发: POST http://127.0.0.1:10809https://api.firecrawl.dev/v2/scrape   ← 畸形
```

所以那个 404 **是客户端拼错 URL 产生的**，与"网络能不能到国外"无关。
典型判别指纹：`firecrawl --status` / `--version` 正常（不带 URL 的命令不受影响），
但任何带 URL 的命令（scrape/search/crawl）恒定 404。

**解法**：`firecrawl-cli/scripts/firecrawl.sh` 在调用前 `export HTTP_PROXY=` 清空代理变量
（含大小写两种写法 + `NO_PROXY='*'`），让 CLI 走直连从而绕开此 bug。
**这只是绕开 CLI bug 的手段，不代表 firecrawl 不能经代理访问。**
根治需要上游修 axios 代理处理，或在 wrapper 里用 `https-proxy-agent` 注入正确 agent。

## Firecrawl（兜底，烧 credits）— 必须走 wrapper

```bash
# Hermes 侧（本机绝对路径）
FC="<skills-path>/firecrawl-cli/scripts/firecrawl.sh"

# 读文章（首选姿势）
bash $FC https://example.com --only-main-content

# JS 渲染页（等 3 秒）
bash $FC https://example.com --wait-for 3000 --only-main-content

# 反爬站（加 basic 代理）
bash $FC https://example.com --proxy basic --only-main-content

# 按 schema 结构化提取
bash $FC https://example.com --schema '{"type":"object","properties":{"title":{"type":"string"}}}'

# 查额度
bash $FC credit-usage --json
```

> ⚠️ **wrapper 自动做两件事**：清空代理变量（绕开 CLI 的 URL 拼装 bug）+ 从 profile `.env` 加载 `FIRECRAWL_API_KEY`。
> **不要裸调 PATH 里的 `firecrawl`**——带代理时恒定 404（判别指纹：`--status` 正常但 `scrape` 404）。
> ⚠️ 该版本 `-o <绝对路径>` 静默失败，落盘请用 shell `>` 重定向。

### 🚫 禁止用 firecrawl search

**firecrawl 仅作抓取，搜索绝不用它**（用户 2026-07-22 纪律）：
- 搜索走 **10r_search（combo）→ Tavily → Exa**
- 需要抓搜索结果页时，先搜索拿到 URL，再对 URL 单独 scrape

## 搜索（10r_search → Tavily → Exa）

```bash
# 🥇 10r_search（主力；Desktop 会话用 CLI，网关多账号轮询容错）
python "E:\AI Output\Hermes-Workspace\scripts\10r_cli.py" search "关键词" --max-results 5

# 🥈 Tavily（直连；作为 10r 失效时的次选）
python <tavily-search>/scripts/tavily_search.py --query "关键词" --max-results 5
python <tavily-search>/scripts/tavily_search.py --query "关键词" --max-results 5 --format md
# 新闻模式
python <tavily-search>/scripts/tavily_search.py --query "AI" --topic news --start-date 2026-09-01

# 🥈 Exa（结构化好，含 publishedDate；按次计费 $0.007）
#    POST https://api.exa.ai/search  header: x-api-key
#    body: {"query": "...", "numResults": 3}

# 🥉 内置 WebSearch（宿主 agent 的 web_search 工具，若可用）
```

> ⚠️ Tavily **不要走本地 router**（`localhost:20128`）——中文 query 会 400。直连 `api.tavily.com`。
> 额度查询：`GET https://api.tavily.com/usage`（Bearer 认证）

## better-webfetch（静态页省额度用）

适用于**确定是干净静态页**的场景（博客、新闻正文、微信公众号文章），免费且快：

```bash
python <better-webfetch>/scripts/fetch.py "URL"
python <better-webfetch>/scripts/fetch.py "URL" --raw-md
```

**已知不适用**（实测）：

| 站点 | 结果 | 改用 |
|------|------|------|
| 知乎 | HTTP 403（反爬硬拦截） | Firecrawl |
| 雪球 | Markdown 转换空输出 | Firecrawl / snowball-cli / 东财 API |
| Wikipedia | 直连超时 15s | `s_wikipedia.py` 官方 API（带代理） |
| 微信公众号 | ✅ 可用（~0.3s，全库最快） | — |
| 国内静态博客 | ✅ 可用 | — |

## ~~Jina Reader~~ — ❌ 已移除（2026-09-15 实测不可达）

`curl -s "https://r.jina.ai/URL"` **直连与走代理均返回 HTTP 000**（443 端口不可达，非限流）。
本机环境下**不可用，不要再作为兜底通道**。若日后网络环境变化需恢复，请先实测再写回本文档。

## RSS (feedparser)

```bash
pip install feedparser
python -c "
import feedparser
for e in feedparser.parse('FEED_URL').entries[:5]:
    print(f'{e.title} — {e.link}')
"
```

## 选择指南（速查）

| 场景 | 推荐工具 |
|-----|---------|
| 搜索信息（无URL） | 10r_search（combo）→ Tavily → Exa |
| agent-reach 覆盖的社媒/平台（自媒体） | Agent-Reach 平台通道；全灭时 Firecrawl scrape |
| 其它通用静态网页 | better-webfetch → 10r_fetch → firecrawl（兜底） |
| JS 渲染 / 反爬 / 需登录 | Firecrawl scrape（`--wait-for` / `--proxy basic`） |
| 墙外站 | better-webfetch 或 Firecrawl，**带代理** |
| Wikipedia | `s_wikipedia.py`（见 wikipedia.md，**带代理**） |
| RSS 订阅 | feedparser |

## 原则

- **搜索走 10r_search → Tavily → Exa；firecrawl 不做 search**
- **社媒/自媒体 → Agent-Reach 平台通道优先；其它静态网页 → better-webfetch（省 credits）**
- **静态页 Fetch 链：better-webfetch → 10r_fetch → firecrawl（兜底）**
- **代理保持开启**（墙外站/Wikipedia/Twitter 都需要）；firecrawl 由 wrapper 内部临时清空
- **firecrawl 一律走 wrapper**（绕开 CLI 的代理 URL 拼装 bug + 加载 key）
- Firecrawl 输出默认到 `.firecrawl/` 目录
