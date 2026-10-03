# 网页工具速查 — 搜索 vs 读取

> ⚠️ 本文与 `web.md` 互为速查/详版，**路由以 `web.md` 为准**。
> 最后修订：2026-09-15 ｜ 改动：对齐 web.md（Firecrawl 优先、去 Jina、禁 firecrawl search、补代理）

## 核心区分

| 目的 | 工具 | 输入 | 输出 |
|------|------|------|------|
| **搜索** (不知道有哪些页面) | Tavily → Exa → WebSearch | 关键词 | 相关链接列表 + snippet |
| **读取** (已有具体 URL) | Firecrawl（首选）/ better-webfetch（静态页省额度） | URL | 页面内容 |

## 三阶工作流

```
① Tavily 搜信息 → ② 社媒/自媒体难点内容用 Firecrawl → ③ 其它静态网页用 better-webfetch
```

| 优先级 | 场景 | 工具 | 原因 |
|:------:|------|------|------|
| 1 🥇 | **信息查询**（无URL） | **Tavily** → Exa → WebSearch | 结构化结果、AI友好、速度快 |
| 2 🥇 | **agent-reach 覆盖的社媒/平台**（自媒体） | **Firecrawl scrape** ✅ | 内容难爬，真实浏览器渲染 + 代理池 |
| 3 🥇 | **其它通用静态网页** | **better-webfetch** ✅ | 免费、最快（~0.3-1.6s） |
| 4 🥈 | **读复杂页面**（JS渲染/登录/交互） | Firecrawl（`--wait-for` / `--proxy basic`） | 完整浏览器渲染 |
| 5 🚨 | **页面变化监控** | Firecrawl monitor | 定时检查、webhook通知 |

## ⚠️ 代理规则（2026-09-15 实测校正）

环境变量 `HTTP_PROXY` / `HTTPS_PROXY` **已设为 `http://127.0.0.1:10809`**。
**总体原则：保持带代理**（墙外站/Wikipedia/Twitter 都需要）；firecrawl 由 wrapper 内部临时清空。

| 工具 | 代理要求 |
|------|---------|
| Wikipedia / Wikidata | **必须带代理**（直连超时 74s，带代理 2.7s） |
| Twitter/X | **必须带代理**（用 `tw_run.py`） |
| 墙外站（GitHub 等） | **必须带代理** |
| firecrawl | **走 wrapper**（内部清代理，绕开 CLI 的 URL 拼装 bug） |

> ⚠️ firecrawl 那个"必须清代理"**不是网络不通**——`curl -x 127.0.0.1:10809` 实测能到达 firecrawl（405）。
> 是 CLI 自己把目标 URL 当路径发给了代理。判别指纹：`--status` 正常但 `scrape` 恒定 404。
> 详见 `web.md`§为什么 firecrawl 要 special-case。

## 搜索工具对比

| 工具 | 收费 | 结构化 | 速度 | 适合场景 |
|------|------|--------|------|---------|
| **Tavily** ✅ 首选 | 免费额度（1000/月） | 好 (title/url/snippet) | 快 | 通用信息查询、新闻搜索、调研、中文 |
| **Exa** ✅ 次选 | $0.007/次 | 好（含 publishedDate） | 快 | 技术/英文内容、需要日期元数据 |
| 内置 WebSearch | 免费 | 中 | 快 | 宿主 agent 可用时的轻量兜底 |
| GH CLI `gh search` | 免费 | 好 (JSON) | 快 | 代码搜索、仓库搜索 |
| ~~firecrawl search~~ | ❌ 烧 credits | — | — | **禁用**（用户 2026-07-22 纪律） |
| ~~Jina `curl r.jina.ai`~~ | ❌ 已不可达 | — | — | **本机 443 不通，已移除** |

## 读取工具对比

| 工具 | JS渲染 | 速度 | 配置 | 适合场景 |
|------|--------|------|------|---------|
| **Firecrawl scrape** ✅ 首选 | 完全 | ~1.5-2s | wrapper 自动带 key | 任何页面；自媒体/反爬/JS 都覆盖 |
| **better-webfetch** 🥈 | ❌ 无 | ~0.3-1.6s | 零配置（本地 Python） | **仅干净静态页**（博客/新闻/微信） |
| ~~Jina Reader~~ | — | — | — | **已移除（不可达）** |
| Hermes Browser | 完全 | ~3-5s | 零配置 | 需交互/登录/填表单（⚠️ 本机缺 Chromium，实际不可用） |

**better-webfetch 已知不适用**：知乎(403) / 雪球(空) / Wikipedia(超时) → 改用 Firecrawl 或专用脚本。

## Firecrawl 命令速查（必须走 wrapper）

```bash
FC="<skills-path>/firecrawl-cli/scripts/firecrawl.sh"

# 读文章
bash $FC https://example.com --only-main-content

# JS 渲染（等 3 秒）
bash $FC https://example.com --wait-for 3000 --only-main-content

# 反爬站（加代理模式）
bash $FC https://example.com --proxy basic --only-main-content

# 结构化提取
bash $FC https://example.com --schema '{"type":"object","properties":{"title":{"type":"string"}}}'

# 交互 / 爬取 / 监控
bash $FC interact "go to amazon, search keyboards, filter by price"
bash $FC crawl https://example.com --limit 50 --wait
bash $FC monitor create --name "Monitor" --schedule "every 5 minutes" --page "URL"

# 额度
bash $FC credit-usage --json
```

> ⚠️ wrapper 自动清代理 + 加载 key。**勿裸调 PATH 里的 `firecrawl`**（代理 bug → 恒定 404）。
> ⚠️ `-o <绝对路径>` 该版本静默失败，落盘用 shell `>` 重定向。
> 🚫 **firecrawl 仅作抓取，禁止用它 search**——搜索走 Tavily。

## 原则

- **社媒/自媒体难爬 → Firecrawl；其它通用静态网页 → better-webfetch**
- **代理保持开启**（墙外站/Wikipedia/Twitter 都需要）；firecrawl 由 wrapper 内部临时清空
- **firecrawl 一律走 wrapper**（绕开 CLI 的 URL 拼装 bug + 加载 key）
- Firecrawl 输出默认到 `.firecrawl/` 目录
