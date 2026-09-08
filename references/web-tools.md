# 网页工具速查 — 搜索 vs 读取

## 核心区分

| 目的 | 工具 | 输入 | 输出 |
|------|------|------|------|
| **搜索** (不知道有哪些页面) | Tavily | 关键词 | 相关链接列表 + snippet |
| **读取** (已有具体 URL) | Firecrawl / Jina / Browser | URL | 页面内容 |

## 三阶工作流（用户偏好）

按优先级击穿：

```
① Tavily 搜信息 → ② Firecrawl 读具体文章 → ③ Firecrawl interact / Browser 处理交互页面
```

| 优先级 | 场景 | 工具 | 原因 |
|:------:|------|------|------|
| 1 🥇 | **信息查询**（无URL） | **Tavily** | 结构化结果、AI友好、速度快 |
| 2 🥈 | **读指定文章**（有URL） | **Firecrawl scrape** ✅ | JS渲染好、干净Markdown、比Jina可靠 |
| 3 🥉 | **读复杂页面**（JS渲染/登录/交互） | **Firecrawl interact** 或 Browser | 完整浏览器渲染 |
| 4 🚨 | **页面变化监控** | **Firecrawl monitor** | 定时检查、webhook通知 |

## 搜索工具对比

| 工具 | 收费 | 结构化 | 速度 | 适合场景 |
|------|------|--------|------|---------|
| **Tavily** ✅ 首选 | 免费额度 | 好 (title/url/snippet) | 快 | 通用信息查询、新闻搜索、比价、调研 |
| GH CLI `gh search` | 免费 | 好 (JSON) | 快 | 代码搜索、仓库搜索 |
| Jina `curl r.jina.ai` | 免费 | 无 (全文) | 快 | ❌ 不能做搜索，只读具体页面 |

## 读取工具对比

| 工具 | JS渲染 | 速度 | 配置 | 适合场景 |
|------|--------|------|------|---------|
| **Firecrawl scrape** ✅ 首选 | 完全 | 快 (~2s) | API Key已配 | 任何网页内容提取，JS重页面也能处理 |
| **Jina Reader** `curl r.jina.ai/URL` | 部分 | 快 (~1s) | 零配置 | Firecrawl不可用时的备选 |
| **Hermes Browser** | 完全 | 慢 (~3-5s) | 零配置 | 需要交互、登录、填表单的页面 |

## Firecrawl 命令速查

```bash
# 搜索
firecrawl search "query" --scrape --limit 3

# 读文章（替代 curl r.jina.ai）
firecrawl scrape "URL" -o .firecrawl/article.md

# 交互
firecrawl interact "go to amazon, search keyboards, filter by price"

# 爬取
firecrawl crawl "URL" --max-pages 50

# 监控
firecrawl monitor create --name "Monitor" --schedule "every 5 minutes" --page "URL"
```

## 原则

- **搜索用 Tavily，读取用 Firecrawl** — 不要反着来
- 不要用 `curl r.jina.ai` 做搜索，它只适合读具体页面
- Firecrawl 已安装，31 个 skills 已就绪（11 个按需已屏蔽）
- Firecrawl 输出默认到 `.firecrawl/` 目录