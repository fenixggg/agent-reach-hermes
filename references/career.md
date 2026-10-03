# 职场招聘 — LinkedIn

> 最后修订：2026-09-15 ｜ 改动：移除已失效的 mcporter 与 Jina 路径

## 现状

⚠️ **本机 LinkedIn 无可用通道**：

| 路径 | 状态 |
|------|------|
| LinkedIn MCP（`mcporter call linkedin-scraper.*`） | ❌ **不可用**：本 profile MCP 已清空，`mcporter` 命令不存在 |
| Jina Reader（`curl r.jina.ai`） | ❌ **不可用**：本机 443 不通，直连与走代理均 HTTP 000 |
| ~~`linkedin.com/in/...` 直接抓取~~ | ❌ 登录墙，公开抓取拿不到正文 |

## 可用的替代路径

```bash
# 1) 通用搜索找公开信息（首选，零配置）
python <tavily-search>/scripts/tavily_search.py --query "site:linkedin.com/in AI engineer" --max-results 5

# 2) 抓具体公开页（走 wrapper；LinkedIn 反爬强，成功率有限）
bash <firecrawl-cli>/scripts/firecrawl.sh "https://www.linkedin.com/in/username" --only-main-content

# 3) 国内招聘场景：改用 BOSS直聘/脉脉等站点走 Tavily 搜索 + Firecrawl 抓取
```

> 如需恢复 LinkedIn MCP：`hermes mcp add linkedin-scraper --command npx --args -y @linkedin/mcp-server`
> （需自行确认包名与凭证），配置后请更新本文档。

## 建议

LinkedIn 抓取本身反爬严格且涉及个人数据，**优先用 Tavily 搜索公开摘要**即可满足大部分调研需求，
不必追求全文抓取。
