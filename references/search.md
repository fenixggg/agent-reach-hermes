# 搜索工具

> 最后修订：2026-09-15 ｜ 改动：移除已失效的 mcporter/Exa MCP 引用，对齐 MEMORY.md 的 fallback 链

## 搜索 fallback 链（2026-10-02 对齐全局纪律）

**Search 一律走：10r_search（engine=combo，主力）→ Tavily → Exa → 内置 WebSearch**

> Desktop 会话插件不注入时用 CLI：`python "E:\AI Output\Hermes-Workspace\scripts\10r_cli.py" search "query"`（多账号轮询容错）。
> ⚠️ **搜索绝不用 Firecrawl**（用户 2026-07-22 纪律）——它的 search 烧 credits，
> 需要抓搜索结果页时，先用上面任一工具拿到 URL，再对 URL 做 scrape。

| 用途 | 方式 |
|------|------|
| 通用网页搜索 | **10r_search（combo）** → Tavily → Exa → 内置 `web_search` |
| 中文搜索 | 10r_search（combo 自动轮询）或 byted-web-search |
| 技术/英文内容 | Exa（结构化好，含 `publishedDate`；$0.007/次） |
| 代码搜索 | GitHub CLI（`gh search code` / `gh search repos`） |

## 命令速查

```bash
# 🥇 Tavily（主力）
python <tavily-search>/scripts/tavily_search.py --query "关键词" --max-results 5
python <tavily-search>/scripts/tavily_search.py --query "关键词" --max-results 5 --format md
# 新闻模式
python <tavily-search>/scripts/tavily_search.py --query "AI" --topic news --start-date 2026-09-01

# 🥈 Exa（REST 直调）
#   POST https://api.exa.ai/search
#   header: x-api-key: $EXA_API_KEY
#   body:   {"query": "...", "numResults": 3}

# 代码搜索
gh search repos "query" --sort stars --limit 10
gh search code "query" --language python --limit 10
```

## 额度查询

```bash
# Tavily（Bearer 认证）
curl -s https://api.tavily.com/usage -H "Authorization: Bearer $TAVILY_API_KEY"
```

> 额度现状见 MEMORY 归档；使用前建议先查 usage，撞到限流才发现属可避免的中断。

## 使用场景

| 场景 | 推荐工具 |
|-----|---------|
| 通用搜索 | Tavily → Exa → `web_search` |
| 技术/英文内容 | Exa |
| 代码搜索 | GitHub CLI (`gh search code`) |
| 站内搜索（微博/雪球/知乎等） | 走 agent-reach 对应平台通道，不用通用搜索 |
