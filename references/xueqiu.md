# 雪球 / Xueqiu (snowball-cli)

## 安装（2026-09-08 已完成，重装/迁移时按此流程）

```bash
npm install -g snowball-cli        # 官方 npm 包（baixianger/snowball-cli 的发行版）
# ⚠️ 本机补丁（npm update/重装会清掉，需重打）:
#    1. esbuild 重编译: npx esbuild <包目录>\index.ts --bundle --platform=node --format=cjs --outfile=<包目录>\dist\index.js
#    2. dist/index.js 头部 ESM require shim 改 createRequire（否则 node24 下 Dynamic require of "fs" 崩溃）
# 3. post <id> 读全文失败的收尾噪音: node libuv 断言 (见下方"已知噪音"节)，非补丁问题
# 
# ── 补丁验证方法（npm update / 重装 / 迁移后必跑）──
#   ⚠️ 判据不能只看文件大小（dist/index.js 正常约 194 KB，有无补丁差异不大）
#   正确做法是三重检查：
#     (a) 注册命令是否生效（最直接）：snowball help | Select-String "search-posts"
#         命中 → 命令已注册；不命中 → 补丁丢失，需按上面步骤 1&2 重打
#     (b) ESM shim 是否在位：搜 dist/index.js 里的 createRequire（应命中 3 处）
#     (c) 崩溃点是否已消：搜 dist/index.js 里的 "Dynamic require"（应命中 0 处；
#         若命中原版报错文案，说明 node24 下会崩，steps 1&2 没生效）
#   实测命令（PowerShell，2026-09-17 验证通过）：
#     $f = "$env:APPDATA\npm\node_modules\snowball-cli\dist\index.js"
#     (Select-String -Path $f -Pattern "search-posts"   -SimpleMatch).Count   # 期望 >=1
#     (Select-String -Path $f -Pattern "createRequire"  -SimpleMatch).Count   # 期望  3
#     (Select-String -Path $f -Pattern "Dynamic require" -SimpleMatch).Count  # 期望  0
#   另：confirm 补丁版 help 的 Social 段应含
#     snowball search-posts <keyword> [--count 10] [--sort relevance|time|reply]
#   
# ⚠️ 注意 search-posts 即便补丁在位也会被 WAF 挡（见下方"关键词搜帖+读全文"节），
#    "注册成功"与"端点可用"是两回事，别把 WAF 403 误判成补丁失效。
# 本机补丁内容: search-posts 命令（关键词搜雪球帖子, 上游 api.ts 有函数但没注册成命令）
```

> 雪球**帖子/讨论内容**的专用工具（行情走东财公开API更快，见下方兜底）。
> v0.3.1，npm 全局安装。专为 AI Agent 设计，JSON 输出。

## 登录态

社交类命令需要登录态（已配置，凭证位置见下方表格）：

```bash
snowball login          # 终端二维码，用雪球App扫码
snowball login --manual # 打开Chrome窗口扫码
snowball token <cookie> # 手动粘贴 DevTools 里的 cookie
snowball status         # 检查登录态
```

## 凭证存放位置（2026-09-08 现状）

| 位置 | 说明 |
|---|---|
| `~/.snowball-cli/token.json`（即 `~/.snowball-cli\`） | **CLI 实际读取的**，含完整 cookie |
| profile `.env` | `SNOWBALL_TOKEN_PATH=%USERPROFILE%\.snowball-cli\token.json`（**仅记录文件路径，不放 cookie 值**） |

- Token 无固定 TTL（雪球 cookie 滑动续期）；失效场景：其他设备登录顶号、风控踢、长期不用
- 失效恢复：`snowball login` 重扫（二维码 2 分钟窗口，自动换码最多 3 次）→ 记得同步更新 `.env` 副本
- 状态检查：`snowball status`（实时在线验证）
- 免登录可用：`quote` / `market` / `fund`

## 社区/讨论类命令（核心价值）

```bash
snowball trending [day|week|month] --count 5   # 全站热帖/KOL文章
```

⚠️ ~~Agent Git Bash 下 `snowball` 命令直接挂~~ **已于 2026-09-14 根治**：根因是 Agent bash 运行时没把 PortableGit 的 `usr/bin`（coreutils 所在）加进 PATH，npm shim 里的 dirname/sed/uname 全部找不到。已在 `E:\Agent\resources\app.asar.unpacked\cli\vendor\shim\shell-runtime-bash-env.sh` 开头加 PATH 前缀修复（备份：同目录 `*.bak-20260914`）。**若 Agent 升级后该文件被覆盖、snowball 再次报 `Cannot find module`，按此重打补丁**；临时绕过可用 node 直调：

```bash
"node" "<npm-global-path>\snowball-cli\cli.js" trending --count 10
# 其他子命令同理，把 trending 换掉即可
```
snowball kol SH600519 --count 10               # 个股的KOL讨论者列表
snowball user <id> --count 10                  # 大V时间线帖子
snowball profile <id>                          # 用户资料
snowball post <id>                             # 单帖详情（正文）
snowball search-user <关键词>                   # 找大V的数字ID
snowball live --important --count 10           # 7x24要闻
snowball feed [headlines|today|a-shares|us|hk|funds]  # 信息流
```

## 行情/财务类（备用，主力走东财API）

```bash
snowball quote SH600519 [--detail]      # 实时行情 / PE PB 股息 52周
snowball kline SH600519 --period day --count 120
snowball market                          # 主要指数
snowball search <关键词>                  # 搜股票代码
# 其他: pankou/minute/income/balance/cashflow/company/holders/flow/margin/screen/fund
```

**代码格式**：`SH600519` 沪 / `SZ000858` 深 / `01810` 港 / `AAPL` 美股 / `110011` 基金

## 推荐工作流（帖子讨论分析）

```bash
# 1. 发现热帖
snowball trending --count 5
# 2. 个股讨论者
snowball kol SH600519 --count 10
# 3. 抓大V时间线
snowball user <id> --count 10
# 4. 读帖子全文
snowball post <id>
```


## 实测状态（2026-09-25 更新，WAF 补丁 v2 已打）

| 能力 | 状态 | 说明 |
|---|---|---|
| `trending` / `kol` / `user` / `feed` / `live` / `hot` | ✅ 全部恢复 | 2026-09-25 WAF 补丁 v2 后实测正常 |
| `quote` / `market` / `fund` | ✅ 免登录可用 | 走 stock.xueqiu.com 不受影响 |
| `search-posts`（本机 patch 新增） | ❌ WAF JS 挑战 | `_waf_bd*` 变体（textarea 挑战页），纯 HTTP 解不了，绕行走下方方案 |
| `post <id>` 读全文 | ❌ WAF 挡 | 同上 |
| `status` | ⚠️ 有误导 | 见下方「假阳性」说明 |

## 🚨 2026-09-25 WAF 事件与补丁 v2（重要，排查必读）

**症状**：`snowball status` 显示 `✓ active`（假阳性），但 `trending/live/feed/user` 等全部返回
`HTTP 400: 400016 "遇到错误，请重新登录帐号后再试"` ——错误文案**误导性极强**，让人以为是 token 失效。

**真根因**（对照实验定案）：雪球 9 月下旬对 `xueqiu.com` 主域接口加了**阿里云 WAF 传输层指纹校验**：
- ① CLI 的 `fetch`(undici) 把请求头全部小写化发送（`cookie:` vs 浏览器 `Cookie:`）→ bot 指纹 → 直接 400
- ② 即使换原生 https，跟随 302 重定向时 undici 不带每跳的 Set-Cookie → 挑战链走不完
- **token 本身根本没失效**（同一 token 在 urllib/浏览器侧恒定 200），**不要重新登录！**

**挑战链（已实测可纯 HTTP 走完）**：
`GET xueqiu.com/statuses/hots.json` → 302 到 `www.xueqiu.com` → 302 到 `query/v1/old/status/hots.json?u=..&uuid=..`（途中 Set-Cookie 逐步完善）→ **200**。

**补丁 v2 内容**（`dist/index.js` 内搜「本机补丁 v2」）：
重写 `request()`：改用 node `https` 原生模块（保留头部大小写）+ 手动 cookie jar + 跟随 302 链（上限 6 跳）。`stock.xueqiu.com` 域接口不受影响，行为不变。备份：`dist/index.js.bak-20260925`。

**补丁验证（npm update/重装后必跑）**：
```powershell
Select-String -Path "$env:APPDATA\npm\node_modules\snowball-cli\dist\index.js" -Pattern "本机补丁 v2" -SimpleMatch   # 期望 >=1
snowball trending --count 2    # 期望返回 JSON 数组而非 400016
```
另注意：v2 用了 `__require` shim（文件头部第 8 行，2026-09-14 那次补丁所加），**两个补丁有依赖关系，重装后都要重打**。

**附带教训**：
- `snowball login` 两条路径都坏了（QR 轮询接口 400 + `--manual` 踩 CLI 自身 `console is not async iterable` bug）→ **恢复登录态用 `snowball token "<cookie串>"`**（F12 复制完整 cookie），不要跟 login 死磕
- `snowball token` 传参时粘的是文档模板占位符（`其他=xxx`）会存进垃圾 cookie 且报 ByteString 错——粘之前核对是真实值
- `snowball status` 的 `✓ active` 只证明 token 格式可读，**不代表 social 接口能通**——判断恢复以 `trending` 出数为准

## 关键词搜帖 + 读全文的可行路径

雪球 WAF 会 JS 挑战部分端点（浏览器可过，纯 HTTP 恒定返回 110KB 挑战页），绕行方案：

1. **发现帖子**：`snowball trending` / `kol <sym>` → `user <id>` 拿帖子列表和 ID
2. **站内关键词搜索**：Tavily 加 `site:xueqiu.com 关键词` 拿帖子 URL（`xueqiu.com/<uid>/<postid>` 格式）
3. **读帖子全文**：用 Firecrawl 渲染帖子页（走 10Router `/v1/web/fetch`，model=firecrawl）——已实测成功，SSR 正文完整含 markdown 图床链接
   - ⚠️ **勿裸调 PATH 里的 `firecrawl` CLI**（2026-09-09 两边都复现过 404）：CLI 的 axios 读到 `HTTP_PROXY/HTTPS_PROXY` 环境变量会把目标 URL 误当"路径"发给本地代理（`http://127.0.0.1https://api.firecrawl.dev/...`）。**这不是网络不通**——经代理 curl 实测可正常到达 firecrawl（2026-09-15）——纯属 CLI bug。正确姿势：
     - **统一走 wrapper**：`bash <firecrawl-cli>/scripts/firecrawl.sh <url> --only-main-content`（内部自动清代理+加载 key）
     - ⚠️ **不要手动 `$env:HTTP_PROXY=''` 清全局代理**——那会连带废掉 Wikipedia/Twitter/墙外站的抓取（它们反而必须带代理）
     - 判断是不是这个坑：`--status` 正常但 `scrape` 恒定 404 → 即此 bug
   - **Agent 侧备选（2026-09-09 实测）**：Tavily `/extract` 端点 + `extract_depth: "advanced"`（服务端渲染可过雪球 WAF），用 `~/.hermes/.env` 的 `TAVILY_API_KEY` 直调（POST api.tavily.com/extract），实测拿到 21.8KB 完整正文+评论区；正文夹在「来源：雪球App」与「风险提示」之间。extract 额度与 search 分开计。
4. 行情兜底走东财 API（见上）

## 兜底与注意

- **行情兜底**（无需登录，最快）：`GET push2.eastmoney.com/api/qt/stock/get?secid=1.600519&fields=f43,f58,f60,f170,f116,f162,f167` → f43价格(÷100) f58名称 f60昨收 f170涨跌(÷100) f116总市值 f162PE(÷100) f167PB(÷100)。secid前缀：沪`1.`深`0.`港`116.`美股`105./106.`
- npm 包装器在 PS 下跑 node 时 stderr 会报 NativeCommandError 噪音，**不影响 JSON 结果**，忽略即可
- **⚠️ 已知噪音（详细，2026-09-17 实测）** —— 两类 stderr 噪音都是无害的，**不要误判为故障**：

  **噪音 1：PowerShell 的 NativeCommandError 包装**
  `snowball` 是 node 程序，PS 5.1 会把子进程写往 stderr 的任何字节都包成
  `NativeCommandError: ... + CategoryInfo : NotSpecified ...`，看起来像报错，其实只是 PS 的转译。
  正常命令（trending/live/quote 等）都会带上，**JSON 结果完全正常**。

  **噪音 2：node libuv 断言（只出现在被 WAF 挡的命令上）**
  ```
  Assertion failed: !(handle->flags & UV_HANDLE_CLOSING), file src\win\async.c, line 94
  ```
  触发条件：`search-posts` / `post <id>` 这两个被雪球 WAF JS 挑战挡掉的端点。
  WAF 返回 HTML 挑战页（非 JSON）→ CLI 抛
  `Error: Unexpected token '<', "<textarea "... is not valid JSON`
  → 异常路径没走正常退出 → node 在 Windows 上收尾时 libuv 断言 → 退出码 `3221226505`（0xC0000409）。
  **这是 CLI 没处理好错误路径导致的收尾噪音，不是补丁问题、不是网络问题、更不是本机环境坏了。**
  判据：只要报错正文是 `Unexpected token '<'` = 命中 WAF，直接改用下方绕行方案即可，无需排查环境。

- 高频调用注意风控，批量抓帖子间隔 2-3 秒
- 帖子正文是全文实读✅（区别于 Tavily 摘要快照⚠️）

## 检测清单（2026-09-17 全量实测基线）

排查"雪球工具是不是坏了"时，按此表逐项对照——**结论应与本表一致**：

| 项目 | 实测结果 | 备注 |
|---|---|---|
| CLI 在 PATH | ✅ `%APPDATA%\npm\snowball.ps1` | v0.3.1 |
| 本机补丁 | ✅ 在位 | 三重检查见文首"补丁验证方法" |
| 登录态 `status` | ✅ `✓ active` | token 8 天前保存仍有效 |
| `market` / `quote` | ✅ 免登录 | 茅台 SH600519 正常 |
| `trending` / `live` / `feed` / `hot` / `kol` / `profile` | ✅ 全部正常 | 登录态社交类 |
| `search-posts` | ❌ WAF 挡 | `Unexpected token '<'` + libuv 断言 |
| `post <id>` | ❌ WAF 挡 | 同上 |
| Firecrawl wrapper 读帖子 | ✅ 抓到完整正文 | 见上方绕行方案 3 |
| 东财 API 兜底 | ✅ 正常 | `f43=125800` → 1258 元 |
