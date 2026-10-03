# Reddit (rdt-cli)

## 安装与登录（2026-09-08 已配置，重装/迁移时按此流程）

```bash
# 安装（PyPI 版本落后，必须从 GitHub 装 v0.4.2+）
pipx install 'git+https://github.com/public-clis/rdt-cli.git'

# 登录 = 从本机浏览器提取 reddit.com cookie（无扫码/OAuth！）
# 前提：某浏览器（Chrome/Firefox/Edge/Brave）已登录 reddit.com
rdt login     # ⚠️ 已有凭据时会显示 "Already authenticated" 短路不刷新，更新必须先 rdt logout
rdt status    # 验证
```

> ⚠️ 本机 Edge 开了 App-Bound Encryption（新版浏览器 cookie 加密），browser-cookie3 普通权限解不开 → `rdt login` 会报 RequiresAdminError。**实际配置方式**：浏览器登录 reddit.com → F12 → Application → Cookies → 复制 `reddit_session` 和 `token_v2` → 手工组装 credential.json（见下方凭证章节）。

## 命令

```bash
# 搜索帖子
rdt search "query" --limit 10

# 读帖子全文 + 评论
# ⚠️ 必须用裸 ID（如 1s332po），带 t3_ 前缀（t3_1s332po）会返回 not_found（2026-10-02 实测）
rdt read POST_ID

# 浏览 subreddit
rdt sub python --limit 20

# 浏览热门
rdt popular --limit 10

# 浏览 /r/all
rdt all --limit 10
```

## 凭证存放位置（2026-09-08 实测更新）

| 项 | 状态 |
|---|---|
| 凭据文件 | `~/.config/rdt-cli/credential.json`（**CLI 实际读取的**，含 reddit_session + token_v2） |
| profile `.env` | `REDDIT_CREDENTIAL_PATH=%USERPROFILE%\.config\rdt-cli\credential.json`（**仅记录文件路径，不放 cookie 值**） |
| 当前状态 | ✅ 有效（2026-09-08 手动配置，reddit_session JWT 有效期至 **2027-03-08**，username: <your_username>，read+write 权限） |
| 重要机制 | rdt-cli 每 7 天自动尝试从浏览器刷新 cookie（browser-cookie3），**但 Edge 开了 App-Bound Encryption 后普通权限解不开**（RequiresAdminError）——所以自动刷新会一直失败并报 "Cookie refresh failed"，**只要 JWT 没过期就无视此警告** |
| 真正失效时 | JWT 到期（2027-03）或 Reddit 主动踢会话。恢复：浏览器登录 reddit.com → F12 → Application → Cookies → 复制 `reddit_session` 和 `token_v2` → 更新 credential.json（需含 cookies/saved_at/username/modhash/last_verified_at 键）和 .env |
| 登录命令的坑 | `rdt login` 只做浏览器 cookie 提取（无扫码/OAuth），且已有凭据时会短路显示 "Already authenticated" 不刷新——更新必须先 `rdt logout` |

## 注意

> **安装**: `pipx install 'git+https://github.com/public-clis/rdt-cli.git'`（PyPI 版本暂时落后，需从 GitHub 装 v0.4.2+）。需要先登录（`rdt login`）才能搜索和阅读。
> 需要登录的功能：`rdt feed --subs-only`（订阅列表）、`rdt saved`（收藏）。
> 建议使用 `--yaml` 输出，对 AI agent 更友好。
