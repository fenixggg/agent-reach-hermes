# 网页阅读

## 推荐工作流

| 场景 | 工具 | 优先级 |
|------|------|:------:|
| 搜索信息（无URL） | **Tavily** | 🥇 |
| 读指定文章（有URL） | **Firecrawl scrape** | 🥈 |
| 读复杂页面（JS/登录/交互） | **Firecrawl interact** 或 Browser | 🥉 |
| 页面变化监控 | **Firecrawl monitor** | 4 |

Firecrawl 已安装，API Key 已配置。31 个 skills 已就绪。

## 通用网页 (Jina Reader) — 备选

Firecrawl 不可用时回退：

```bash
curl -s "https://r.jina.ai/URL"
```

## Firecrawl (首选用法)

```bash
# 搜索
firecrawl search "query"

# 提取页面内容（替代 curl r.jina.ai）
firecrawl scrape "https://example.com" -o article.md

# 页面交互
firecrawl interact "do something on page"

# 监控页面变化
firecrawl monitor
```

## Hermes Browser — 复杂页面

适用于需要交互的页面（SPA、登录、表单填写等）。

## RSS (feedparser)

```bash
pip install feedparser
python -c "
import feedparser
for e in feedparser.parse('FEED_URL').entries[:5]:
    print(f'{e.title} — {e.link}')
"
```

## 选择指南

| 场景 | 推荐工具 |
|-----|---------|
| 通用文章（有URL） | Firecrawl scrape |
| 搜索信息（无URL） | Tavily |
| 复杂页面（JS渲染） | Firecrawl interact / Hermes Browser |
| RSS 订阅 | feedparser |