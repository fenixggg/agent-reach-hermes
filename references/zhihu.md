# 知乎 / Zhihu（官方 Zhihu CLI）

> ⚠️ **本机有两套知乎 CLI，勿混淆**（2026-09-24 确认）：
> - `zhihu` 命令（PATH）= **pyzhihu-cli v0.2.4**（社区版，uv tool 安装，本文档主体描述的就是它），凭证在 `~/.zhihu-cli/cookies.json`
> - `zhihu-cli.exe` = 官方数据开放平台 CLI（`~\AppData\Local\ZhihuCLI\current\`，走 ZHIHU_ACCESS_SECRET 环境变量，见下方「官方 CLI」节）
> - 两者命令集完全不同：社区版有 `search/hot/question` 等；官方版是 `search zhihu --query` / `search global` / `answer` / `quota`

## 社区版 zhihu（pyzhihu-cli）——登录与凭证（2026-09-24 实测更新）

```bash
zhihu status    # 查登录态（显示 Authenticated ≠ 真有效，必须 whoami 验证）
zhihu whoami    # ✅ 真实校验：Session expired 就是这里暴露
zhihu login --qrcode   # ⚠️ 实测不可用（见下）
zhihu login --cookie "z_c0=...; d_c0=...; _xsrf=..."   # ✅ 唯一可靠登录方式
```

### ⚠️ 二维码登录在本机不可用（2026-09-24 四连败实录）
- CLI 轮询 `scan_info` 接口**全程 HTTP 403**——二维码会话被服务端风控拒绝，与用户扫码姿势无关
- 症状：用户已扫码但手机**不弹确认页**，2 分钟后超时 `未获取到 z_c0`
- **别再试 --qrcode，直接走 cookie**

### Cookie 登录标准流程（凭证不进对话/命令行参数）
1. 用户浏览器 F12 → Application → Cookies → `zhihu.com`，取 3 个键：**z_c0**（`2|1:0` 开头，登录凭证本体）、**d_c0**、**_xsrf**
2. 用户把 `z_c0=xxx; d_c0=yyy; _xsrf=zzz` 存入临时文件（如 workspace 下 `zhihu_cookie.txt`）
3. Agent：`$raw = (Get-Content <临时文件> -Raw).Trim(); zhihu login --cookie "$raw"`
4. 验证：`zhihu whoami` 返回用户信息即成功
5. **删除临时文件**（凭证落盘只在 `~/.zhihu-cli/cookies.json`）
- 2026-09-24 实测：cookie 登录一次成功，search/whoami 恢复正常

### ⚠️ Access denied / 「荒原」排障流程（2026-10-02 实测补充）
`zhihu question <id>` / `answers <id>` 报 `Access denied — check login status` 时，**先别怀疑 Cookie**，按顺序排查：
1. `zhihu whoami` 验证登录态——返回用户信息 = Cookie 有效
2. 同一 URL 用 Firecrawl scrape 交叉验证：也返回「你似乎来到了没有知识存在的荒原」拦截页 = **帖子本身被风控/删除/设权限**（帖子级行为，非站点级，Cookie 和重试都无效）
3. 内容仍需要时的替代通道：官方 CLI 知乎直答 `zhihu-cli.exe answer --query '<问题>'`（检索增强，能把梗概补全）；或用 `zhihu search` 的摘要凑合
- 典型案例：疯四考古中《"星期四"为何"疯狂"不停》一帖（ID 659714252），whoami 正常但 question/answers 双 404+荒原，Firecrawl 同拦，最后靠官方 CLI answer 补全模因三要素内容

### 凭证存放位置
| 位置 | 说明 |
|---|---|
| `~/.zhihu-cli/cookies.json` | **CLI 实际读取的**（社区版） |
| profile `.env` | `ZHIHU_CREDENTIAL_PATH=%USERPROFILE%\.zhihu-cli\cookies.json`（仅登记路径，2026-09-24 加入） |

## 安装与初始化（2026-09-08 已完成，重装/迁移时按此流程）

官方 Skill 包（含 setup 脚本，会自动从官方 CDN 下载带四重校验的 CLI 二进制）：

```
请下载安装 zhihu-cli skill 并完成初始化配置
https://developer-cdn.zhihu.com/zhihu-cli/releases/stable/skill/zhihu-cli-skill.zip
```

安装流程（Windows）：

```powershell
# 1. 下载并解压 zip 到 <profile>/skills/zhihu/
# 2. 状态检查
powershell -ExecutionPolicy Bypass -File <skill-dir>\scripts\run.ps1 status
# 3. 安装 CLI 二进制（自动从 developer-cdn.zhihu.com 下载, SHA-256+大小+域名+版本四重校验, 装到用户目录不动PATH）
powershell -ExecutionPolicy Bypass -File <skill-dir>\scripts\setup.ps1
# 4. 配置 Access Secret（stdin 方式, 不进命令行参数）
#    密钥从 https://developer.zhihu.com/profile 生成（可能需实名认证）
#    ⚠️ auth set --secret-stdin 会因用户数据接口未开通返回 AUTH_INVALID → 改用环境变量方式, 见下方凭证章节
```

> 知乎内容**优先走官方 CLI**（developer.zhihu.com 数据开放平台，first-party），因为 CLI 返回的是**摘要**而非全文。
> 需要**正文全文**时走 **Firecrawl scrape**（走 wrapper，自动清代理）。
>
> ⚠️ **Firecrawl 抓知乎是「部分成功」，不是稳定通道**（2026-09-15 复测）：
>
> | URL | 结果 |
> |---|---|
> | `zhuanlan.zhihu.com/p/27446053999`（2026-09-12 验证过） | ✅ 成功，2185 字符完整正文 |
> | `zhuanlan.zhihu.com/p/216338878` | ❌ 返回「你似乎来到了没有知识存在的荒原」拦截页 |
> | `www.zhihu.com/question/19550224` | ❌ 同上 |
>
> **规律**：能否抓取取决于该帖的风控状态/热度，非站点级统一行为。**抓之前先看返回内容**——
> 若正文含「没有知识存在的荒原」或长度 < 500 字符，即为拦截页，**不要当成正文使用**。
> 拦截后重试通常无效，改用：`zhihu-cli answer`（直答，带检索增强）或接受只有摘要。
>
> ⚠️ **不要在验证场景里用裸 curl/urllib 判断知乎链接死活**——403 是 WAF，不是死链，会得到假阴性。
> ⚠️ 走 wrapper：`bash <firecrawl-cli>/scripts/firecrawl.sh <url> --only-main-content`
> （裸调 PATH 里的 firecrawl 在带代理时会因 CLI 把 URL 当路径发给代理而恒定 404——
> **那不是网络不通**，是 CLI bug；wrapper 内部清代理即可绕开）。

> 当前二进制 v0.5.0 @ `$env:LOCALAPPDATA\ZhihuCLI\current\zhihu-cli.exe`（2026-09-08 安装）。
> 官方 skill 文档 zip 里含 references/cli.md（全参数表）、http-api.md 等权威参考。

## 路径与调用方式

```powershell
# 二进制绝对路径（不依赖 PATH）
$cli = "$env:LOCALAPPDATA\ZhihuCLI\current\zhihu-cli.exe"
# ⚠️ Hermes 终端里 & $cli args 会被误判为后台化而拒绝执行
# 必须包一层：
powershell -Command "& '$cli' search zhihu --query '关键词' --count 5"

# Agent 侧（2026-09-09 实测）：
# ❌ 不要用 powershell -Command 包一层 —— Agent 的 PowerShell 工具在该机器上 stdout 捕获失效
#    （连 Write-Output 基线都拿不到输出），会得到假阴性"空输出但 exit 0"
# ❌ Bash 里调 powershell.exe 会被安全检查直接拦截
# ✅ Git Bash 直接调 exe（JSON 输出完整可读）：
"$env:LOCALAPPDATA\ZhihuCLI\current\zhihu-cli.exe" hot --limit 20
```

## 凭证存放位置（2026-09-08 现状）

| 位置 | 说明 |
|---|---|
| Windows 用户环境变量 `ZHIHU_ACCESS_SECRET` | **CLI 实际读取的**（读取顺序：环境变量 > 系统密钥链），已持久化 |
| profile `.env` | 无该键（**值只放用户环境变量，不入 .env**——40 字符短值有环境变量兜底即可） |
| 系统密钥链（Windows Credential Manager） | 空（auth set 因用户数据接口未开通而失败，未写入） |

- 凭证读取顺序：环境变量 > 系统密钥链 > AUTH_REQUIRED
- ⚠️ `auth set --secret-stdin` 会返回 AUTH_INVALID（当前账号用户数据接口未开通），**公开内容接口不受影响**；若要开通本人数据，去 developer.zhihu.com/profile 检查实名认证/权限
- 换密钥：`[Environment]::SetEnvironmentVariable("ZHIHU_ACCESS_SECRET","<新值>","User")` + 同步更新 profile `.env`

## 常用命令速查

```powershell
# ⚠️ 以下 powershell -Command 包装方式仅适用于 Hermes 侧
#    Agent 侧不要用（其 PowerShell stdout 捕获失效），见上方「路径与调用方式」的 Git Bash 直调
# 搜知乎（返回标题/作者/摘要/Url/赞同数/评论数；摘要非全文）
powershell -Command "& '$cli' search zhihu --query '关键词' --count 5"

# 搜全网（站外新闻/官网，--search-db all|realtime|static）
powershell -Command "& '$cli' search global --query '关键词' --count 5"

# 知乎热榜（最多 30 条）
powershell -Command "& '$cli' hot --limit 20"

# 知乎直答（检索增强AI答案；模型 zhida-fast-1p5 | zhida-thinking-1p5 | zhida-agent）
powershell -Command "& '$cli' answer --query '问题'"

# 本人数据（当前账号未开通，AUTH_INVALID）：me contents / me followees / me favorites ...
# 额度查询（不消耗业务额度）
powershell -Command "& '$cli' quota"
```

## 额度（邀测期免费，自然日重置）

| 能力 | 每日额度 |
|---|---:|
| 知乎搜索 / 全网搜索 | 各 5,000 |
| 知乎用户数据 | 10,000 |
| 知乎热榜 / 知乎直答 | 各 100 |
| 知识库 | 500 |
| 小工具 | 10 |

## 使用边界

- `search` 返回的是**摘要**不是全文；读原文仍需配合网页抓取（知乎正文对抓取不友好，直答可做补充）
- 热榜适合发现议题，不等于事实核查
- 直答用于快速综合，深度研究优先用搜索拿原始来源
- 错误处理：`Code: 30001` 频率限制（停止重试）、`Code: 30002` 配额耗尽、退出码非 0 即失败（即使 HTTP 200 内含业务错误）
- 安全：不在回复/日志中复述完整 Access Secret；泄露后去个人中心删除重申
