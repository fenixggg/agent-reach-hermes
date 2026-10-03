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
# ⭐ 搜索（agent 首选）：泛化包装脚本，紧凑输出每帖 2-3 行，自动规避 --yaml 尺寸炸弹与 JSON 缺陷
#   支持裸 ID/t3_ 前缀/reddit URL；--json 出信封；--save-to 落盘 UTF-8 无 BOM
python <skill-path>/scripts/rdt_search.py "query" --limit 10 --snip 220

# ⭐ 读帖 + 评论（agent 首选）：双路径解析（严格 JSON → 失败自动降级正则提取），
#   评论按赞数排序，--max-comments/--max-body 控制 token
python <skill-path>/scripts/rdt_read.py <POST_ID或URL> --max-comments 30 --max-body 700

# 裸 rdt 命令（人工调试用，agent 慎用，原因见下方已知坑）
rdt search "query" --limit 10
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

## ⚠️ 已知坑与 agent 用法（2026-10-03 实测，v0.4.2）

| 症状 | 根因 | 处置 |
|---|---|---|
| `read --json` 输出**间歇性**非法 JSON（comments 数组后跟无键名的裸 ID 数组），`ConvertFrom-Json`/`json.loads` 必炸 | rdt-cli 序列化 bug | 用 `scripts/rdt_read.py`：先走严格 JSON，失败自动降级正则提取五元组（author/body/parent/score），坏样本单测覆盖可 100% 恢复内容 |
| `search --yaml` 单次可吐 **35 万字符**（含帖子全文+HTML），瞬间撑爆 agent 上下文 | yaml 输出含全部元数据+正文 | **agent 禁用 --yaml**（旧版文档"建议 --yaml"已作废）；用 `scripts/rdt_search.py`（--json + 紧凑字段，每帖 2-3 行） |
| `read --json` 是否走严格路径成功**因帖而异** | bug 触发条件未知（同帖不同时段表现不同） | 双路径包装脚本已兜底，输出统一，无需人工判别 |
| 搜索相关性一般，泛词混入无关结果 | Reddit 搜索本身特性 | 拆具体关键词多次搜（dental / MRI / hospital experience 分开），再按 score/num_comments 筛 |
| `rdt read` 带 `t3_` 前缀报 not_found（2026-10-02 实测） | CLI 只认裸 ID | `rdt_read.py` 的 ID 归一化已自动处理（URL/t3_ 前缀/裸 ID 均可） |
| stderr 恒有 `Cookie refresh failed; using existing cookies` | Edge App-Bound Encryption 导致自动刷新失败 | 无害警告，JWT 没过期就无视（见上方凭证章节） |
