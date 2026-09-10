# GitHub (gh CLI)

GitHub 官方命令行工具，用于仓库、Issue、PR、Actions、Release 以及 API 访问。支持通过环境变量或 gh auth login 认证。

### 认证

GitHub Token 已配置在 Hermes `.env` 中，`gh` 通过环境变量自动读取。

```bash
gh auth status
```

### 常用命令

```bash
# 搜索
gh search repos "query" --sort stars --limit 10
gh search code "query" --language python

# 仓库
gh repo view owner/repo
gh repo clone owner/repo

# Issues
gh issue list -R owner/repo --state open
gh issue view 123 -R owner/repo

# Pull Requests
gh pr list -R owner/repo --state open
gh pr view 123 -R owner/repo

# Actions / CI
gh run list --repo owner/repo --limit 10
gh workflow list --repo owner/repo

# API
gh api /user
gh api repos/owner/repo

# JSON 输出
gh issue list --repo owner/repo --json number,title --jq '.[] | "\(.number): \(.title)"'
```

### Windows PowerShell 实战坑（2026-09 实测，sst/opencode 案）

1. **仓库改名/迁移后 search API 报 422**："The listed users and repositories cannot be searched..."。原因：REST 端点（repos/releases/issues list）自动跟随重定向，但 `search/issues` **不跟随**。对策：先 `gh repo view 旧owner/repo --json nameWithOwner` 拿新全名（实测 sst/opencode → anomalyco/opencode），之后 search 一律用新名字。
2. **Hermes 终端包装层吞单引号/复杂引号**：`--jq '.[] | "\(.x)"'` 这类带空格/引号的参数会被拆碎或转义失败（报 accepts 1 arg(s) received N / unterminated string）。对策：URL query 用 `+` 连接保持无空格；jq 用无空格紧凑写法；复杂 jq 直接省略 `--jq` 拿裸 JSON。
3. **`gh issue list -R x --search "..."` 在改名仓库上会静默返回空**（不报错），不可靠；改用 `gh api "search/issues?q=repo:新全名+is:issue+关键词1+关键词2"`。