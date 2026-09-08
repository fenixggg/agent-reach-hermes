# Reddit (rdt-cli)

## 命令

```bash
# 搜索帖子
rdt search "query" --limit 10

# 读帖子全文 + 评论
rdt read POST_ID

# 浏览 subreddit
rdt sub python --limit 20

# 浏览热门
rdt popular --limit 10

# 浏览 /r/all
rdt all --limit 10
```

## 凭证存放位置与维护说明

| 项 | 说明 |
|---|---|
| 凭据文件 | `~/.config/rdt-cli/credential.json`（**CLI 实际读取的**，含 reddit_session + token_v2） |
| profile `.env` | 可作为灾备副本（配置 `REDDIT_SESSION` + `REDDIT_TOKEN_V2`），便于 credential.json 丢失时手动重建 |
| 重要机制 | rdt-cli 每 7 天自动尝试从浏览器刷新 cookie（browser-cookie3）。若浏览器开启了 App-Bound Encryption（如 Chromium 系列），自动刷新可能受权限限制报错 "Cookie refresh failed"；只要 JWT 凭证尚未过期，此类警告通常不影响正常调用 |
| 失效恢复流程 | 浏览器登录 reddit.com → F12 → Application → Cookies → 复制 `reddit_session` 和 `token_v2` → 填入 `credential.json`（包含 cookies/saved_at/username/modhash/last_verified_at） |
| 登录更新注意 | `rdt login` 默认做本地浏览器 cookie 提取，若已存在凭据可能会提示 "Already authenticated" 跳过刷新；若需更新建议先 `rdt logout` 或直接编辑配置文件 |

## 注意

> **安装**: `pipx install 'git+https://github.com/public-clis/rdt-cli.git'`（PyPI 版本暂时落后，需从 GitHub 装 v0.4.2+）。需要先登录（`rdt login`）才能搜索和阅读。
> 需要登录的功能：`rdt feed --subs-only`（订阅列表）、`rdt saved`（收藏）。
> 建议使用 `--yaml` 输出，对 AI agent 更友好。
