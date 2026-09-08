# 雪球 / Xueqiu (snowball-cli)

> 雪球**帖子/讨论内容**的专用工具（行情走东财公开API更快，见下方兜底）。
> v0.3.1，npm 全局安装 2026-09-08。专为 AI Agent 设计，JSON 输出。

## 登录态

# 社交类命令需要登录态（已配置，凭证位置见下方表格）

```bash
snowball login          # 终端二维码，用雪球App扫码
snowball login --manual # 打开Chrome窗口扫码
snowball token <cookie> # 手动粘贴 DevTools 里的 cookie
snowball status         # 检查登录态
```

## 凭证存放位置与维护说明

| 位置 | 说明 |
|---|---|
| `~/.snowball-cli/token.json` | **CLI 实际读取的**，含完整 cookie |
| profile `.env` 的 `SNOWBALL_COOKIE` | 可作为灾备副本；token.json 丢失时用 `snowball token "<.env里的值>"` 恢复 |

- Token 无固定 TTL（雪球 cookie 滑动续期）；失效场景：其他设备登录顶号、风控踢、长期不用
- 失效恢复：`snowball login` 重扫（二维码 2 分钟窗口，自动换码最多 3 次）→ 记得同步更新 `.env` 副本
- 状态检查：`snowball status`（实时在线验证）
- 免登录可用：`quote` / `market` / `fund`

## 社区/讨论类命令（核心价值）

```bash
snowball trending [day|week|month] --count 5   # 全站热帖/KOL文章
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


## 实测状态（2026-09-08，登录态已配置）

| 能力 | 状态 | 说明 |
|---|---|---|
| `trending` / `kol` / `user` / `feed` / `live` / `hot` | ✅ 直接可用 | 已实测返回正常 JSON |
| `quote` / `market` / `fund` | ✅ 免登录可用 | |
| `search-posts`（本机 patch 新增） | ⚠️ 被 WAF 挡 | 雪球对 `search.json` 端点做阿里云 WAF JS 挑战，纯 HTTP 客户端过不去 |
| `post <id>` 读全文 | ⚠️ 被 WAF 挡 | `show.json` 同样被封锁 |

## 关键词搜帖 + 读全文的可行路径

雪球 WAF 会 JS 挑战部分端点（浏览器可过，纯 HTTP 恒定返回 110KB 挑战页），绕行方案：

1. **发现帖子**：`snowball trending` / `kol <sym>` → `user <id>` 拿帖子列表和 ID
2. **站内关键词搜索**：Tavily 加 `site:xueqiu.com 关键词` 拿帖子 URL（`xueqiu.com/<uid>/<postid>` 格式）
3. **读帖子全文**：用 Firecrawl 渲染帖子页（走 10Router `/v1/web/fetch`，model=firecrawl）——已实测成功，SSR 正文完整含 markdown 图床链接
4. 行情兜底走东财 API（见上）

## 兜底与注意

- **行情兜底**（无需登录，最快）：`GET push2.eastmoney.com/api/qt/stock/get?secid=1.600519&fields=f43,f58,f60,f170,f116,f162,f167` → f43价格(÷100) f58名称 f60昨收 f170涨跌(÷100) f116总市值 f162PE(÷100) f167PB(÷100)。secid前缀：沪`1.`深`0.`港`116.`美股`105./106.`
- npm 包装器在 PS 下跑 node 时 stderr 会报 NativeCommandError 噪音，**不影响 JSON 结果**，忽略即可
- 高频调用注意风控，批量抓帖子间隔 2-3 秒
- 帖子正文是全文实读✅（区别于 Tavily 摘要快照⚠️）
