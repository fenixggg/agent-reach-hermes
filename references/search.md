# 搜索工具

## Hermes 内置搜索
在当前 Hermes 环境中，搜索推荐使用以下方式：

| 用途 | 方式 |
|------|------|
| 通用网页搜索 | `web_search` 工具或 Tavily |
| 代码搜索 | GitHub CLI (`gh search code`) |
| 中文搜索 | 使用 Tavily 或搜索引擎 API |

## Exa AI 搜索 (如已配置 MCP)

```bash
mcporter call 'exa.web_search_exa(query: "query", numResults: 5)'
mcporter call 'exa.get_code_context_exa(query: "code question", tokensNum: 3000)'
```

## 使用场景

| 场景 | 推荐工具 |
|-----|---------|
| 通用搜索 | Hermes `web_search` / Tavily |
| 技术/英文内容 | Exa (如已配置 MCP) |
| 代码搜索 | GitHub CLI (`gh search code`) |