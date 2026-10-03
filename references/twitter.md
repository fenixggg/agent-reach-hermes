# Twitter/X (twitter-cli)

> 状态：**✅ 可用（2026-09-14 修复）**。`feed` / `user-posts` / `user` / `tweet` / `search` 全部实测 RC=0。
> 关键前提：**必须走用户自己的 VPN 代理**（见下节），且 `search` 需要已打 POST 补丁。

## 🚀 首选调用方式：`tw_run.py` 包装器

不要裸调 `twitter`。Agent 会向子进程注入一个**每会话变化**的代理端口，裸调必然连接失败。

```bash
# Agent 侧（managed python）
python "<skills-path>\agent-reach\scripts\tw_run.py" search "OpenAI" -n 10 --json
python "<skills-path>\agent-reach\scripts\tw_run.py" user-posts @sama -n 20 --yaml

# ⚠️ PowerShell 下 @sama 必须加引号（"sama" 或 '@sama'）——裸 @xxx 会被解析为 splatting 语法
# 导致参数丢失（RC=2 Missing argument）。bash/WSL 下不受影响。

# Hermes 侧
python "<skills-path>\agent-reach\scripts\tw_run.py" search "OpenAI" -n 10 --json
```

`tw_run.py` 自动做三件事：① 从注册表 `HKCU\Environment` 读**用户级**真代理并强制覆盖注入代理（不硬编码端口）；② 从 `~/.hermes/.env` 与 Hermes profile `.env` 读凭证；③ 透传参数、原样返回退出码。
手动指定代理：`tw_run.py --_proxy http://127.0.0.1:10809 search "..."`。

## 安装与登录（2026-09-08 已配置，重装/迁移时按此流程）

```bash
pipx install twitter-cli        # 确保 v0.8.5+
```

> 凭证走 profile `.env` 的 `TWITTER_AUTH_TOKEN` + `TWITTER_CT0`（CLI 自动读环境变量，无需登录命令）。cookie 获取：浏览器登录 x.com → F12 → Application → Cookies → twitter.com → 复制 `auth_token` 和 `ct0` 值 → 更新 .env。

## 稳定命令

```bash
twitter feed -n 20               # 首页时间线
twitter tweet URL_OR_ID          # 单条推文（含回复）
twitter article URL_OR_ID        # 长文 / X Article
twitter user-posts @username -n 20
twitter user @username
twitter search "query" -n 10     # ⚠️ 需先打 POST 补丁，见下节
```

## 输出格式

- `--json` / `--yaml`：结构化输出，喂 LLM 首选
- `--type [top|latest|photos|videos]`、`--from`、`--to`、`--lang`、`--since`、`--until`、`--has`、`--exclude`、`--min-likes`、`--min-retweets`：search 的高级过滤
- ✅ `-c, --compact` 存在（顶层参数，`twitter --help` 可见；2026-10-02 更正：早期"实测不存在"的结论只查了子命令层，是误诊）

## 🚨 故障与修复记录（2026-09-14 实测，已闭环）

### 故障 A：连接失败 `Connection timed out` / `Connection closed abruptly` / `HTTP 0`

**根因：Agent 注入的进程级代理出口到不了 x.com。**
Agent 桌面端启动 agent 时注入 `HTTP_PROXY=127.0.0.1:<随机端口>`（实测两次分别为 64768、52569，**每次会话都变**，且不写系统环境变量，用户在系统设置里看不到）。该出口只能通 `api.firecrawl.dev` / `api.tavily.com`，到不了 x.com。用户自己真实的 VPN 代理写在 **用户级环境变量** `HKCU\Environment`（实测 `127.0.0.1:10809`）。

**修复：** 强制把 `HTTP(S)_PROXY` 指向用户级真代理 → `tw_run.py` 已封装，无脑用它即可。
**排除项：** ❌ 不是凭证问题（auth_token 40 位 hex / ct0 160 位 hex 形貌正常且已载入）❌ 不是网络（`curl https://x.com` 走 10809 直连 HTTP 200）。

> 注：注入端口不要硬编码——用 `tw_run.py` 从注册表动态读。

### 故障 B：`search` 恒定 `HTTP 404`（**已修复**）

**根因：x.com 只接受 POST 调 SearchTimeline，GET 一律 404（空 body）。**

决定性对照实验（同一 cookie、同一 header、同一 queryId）：

| 请求 | 结果 |
|---|---|
| `GET  /i/api/graphql/Yw6L66Pw54NHKuq4Dp7b4Q/SearchTimeline` | ❌ HTTP 404，body 长度 0 |
| `POST /i/api/graphql/Yw6L66Pw54NHKuq4Dp7b4Q/SearchTimeline` | ✅ HTTP 200，44974 bytes，真实搜索结果 |
| `GET  .../HomeTimeline`（对照） | ✅ HTTP 200 |

关键点：**同一个 queryId 换 POST 就通** → 与 queryId 无关。

**已被证伪的两个旧结论（2026-09-14 早期误诊，勿再采信）：**
1. ❌ ~~"`Failed to init ClientTransaction` 会导致全部命令 404"~~ —— **假的**。该 warning 是非致命的，`feed` / `user-posts` / `user` / `tweet` 在带此 warning 的情况下全部正常返回。它只说明缺 `X-Client-Transaction-Id` 头，而该头对多数端点并非必需。
2. ❌ ~~"search 404 是因为 queryId 过期"~~ —— **假的**。客户端本就有 stale-fallback 重试逻辑（`client.py:875`），实测日志确认 `Retrying SearchTimeline with live queryId after 404` **已触发**，用社区维护的 live queryId（`Yw6L66Pw54NHKuq4Dp7b4Q`，来自 twitter-openapi）重试**仍然 404**。queryId 不是变量。

**修复补丁（3 处改动，`use_post` 默认 False 向后兼容）：**

```python
# twitter_cli/client.py
# 1. _fetch_timeline() 签名末尾增加 use_post=False
# 2. 内部分发：
            if use_post:
                data = self._graphql_post(operation_name, variables, FEATURES)
            else:
                data = self._graphql_get(operation_name, variables, FEATURES, field_toggles=field_toggles)
# 3. fetch_search() 的 self._fetch_timeline(...) 调用末尾增加 use_post=True
```

**🔴 2026-09-16 复现记录（第二次踩坑）：补丁会静默丢失，`search` 又变回 404。**
症状：`twitter status` 返回 `authenticated: true`、`feed`/`whoami` 全部正常，唯独 `search` 恒定 `HTTP 404`（连 `--from`、`--type latest` 都 404）。
根因：**补丁被上游覆盖**（`uv tool upgrade` / 重装 twitter-cli 都会重写 `client.py`）。
诊断一行命令（必跑）：
```powershell
$env:PATH = "$env:APPDATA\uv\tools\twitter-cli\Scripts;$env:PATH"
python <agent-reach>\scripts\patch_twitter_search_post.py --check   # 输出 "未打补丁" = 就是这个问题
python <agent-reach>\scripts\patch_twitter_search_post.py           # 重打，输出 "已打补丁"
```
⚠️ **本机 twitter-cli 是 `uv tool` 装的，不是 pipx**，venv python 路径为
`~\AppData\Roaming\uv\tools\twitter-cli\Scripts\python.exe`
（文档旧文写的 `~/pipx/venvs/...` 路径在本机不存在）。把该 Scripts 目录临时加进 `$env:PATH` 即可用普通 `python` 调用补丁脚本 —— 注意**不要用 `&` 调用操作符**，Hermes 的 terminal 层会把 `&` 误判为后台符而直接拒绝执行。

**幂等重打脚本**（`pipx upgrade` / `uv tool upgrade twitter-cli` 会覆盖补丁，升级后重跑即可）：

```bash
# 必须用 twitter-cli 所在 venv 的 python
python <agent-reach>/scripts/patch_twitter_search_post.py          # 打补丁
python <agent-reach>/scripts/patch_twitter_search_post.py --check  # 查状态
python <agent-reach>/scripts/patch_twitter_search_post.py --revert # 还原
```

补丁留了 `.bak` 备份。已实测：`search -n 3` / `search -n 25`（分页）/ `--from` / `--lang --min-likes` / `--type latest` 全部 RC=0 返回真实数据。

**上游适配后应做的事：** 等 `twitter-cli` > 0.8.5 或 `xclienttransaction` > 1.0.3 发布后 `pipx upgrade twitter-cli`，然后跑 `--revert` 再验证是否已原生支持 POST；若已支持则不再需要补丁。

### 版本现状（2026-09-14 核查）

| 包 | 本机 | PyPI 最新 | 备注 |
|---|---|---|---|
| twitter-cli | 0.8.5 | 0.8.5 (2026-03-17) | 已是上游最新 → **升级无用，只能本地打补丁** |
| xclienttransaction | 1.0.3 | 1.0.3 (2026-06-26) | 已是上游最新 |

### 其他注意

- **IP 风控**：不要在 VPS/数据中心 IP 上频繁调用，尤其 followers/following，有封号风险。用住宅代理或本地环境。
- **`likes`**：2024 年后平台限制，只能看自己的。
- **Firecrawl 不支持抓 x.com**（返回 `403 we do not support this site`）。
- **无 VPN 时的兜底**：Tavily 搜索 `include_domains:["x.com","twitter.com"]` 可拿到被索引的公开推文（含原文链接），但拿不到登录墙后内容。

## 📰 当日热点扫描（可复用工作流）

X **没有公开的趋势榜接口**，且**纯过滤词查询会被服务端拒绝**——实测 `search --min-likes 5000 --since <今天>`（无关键词）返回 `BadRequest: SearchQueryParsingException(ERROR_NONCLOSE_FORM)`。所以"当日热点"只能用**主题关键词 × 互动门槛 × 日期窗口**多路扫描后聚合排序。

已固化为脚本：

```bash
python <agent-reach>/scripts/x_hot_topics.py --accounts         # 全量：26 主题 + 7 账号时间线（⚠️ --accounts 必须显式传，默认不抓时间线）
python <agent-reach>/scripts/x_hot_topics.py                    # 仅 26 主题（不含账号时间线）
python <agent-reach>/scripts/x_hot_topics.py --hours 24         # 只保留近 24h
python <agent-reach>/scripts/x_hot_topics.py --themes ai,nvidia # 只跑指定主题
python <agent-reach>/scripts/x_hot_topics.py --out x_hot.json   # 原始数据落盘
```

- 排序权重：`赞 + 2×转推 + 3×引用 + 0.5×回复`。**浏览量不加权**（易被算法放大）。
- 并发默认 6，别调太高（X 有风控）。
- 主题集与账号池在脚本顶部 `THEMES` / `ACCOUNTS` 里，按需增删。

### ⚠️ 热点扫描的两个硬教训（2026-09-14 实测）

1. **`--json` 别忘传**。漏了会静默降级成 YAML 输出，`json.loads` 解析失败 → 表面看像"全部搜索失败"，实际数据是全的。批量脚本里务必显式带上。
2. **互动量高 ≠ 事实为真**。2026-09-14 的扫描里，传播量最大的 6 条传闻有 2 条无正规来源、3 条真实但被显著放大。**输出给用户前必须做外部核实**，否则等于转述谣言。典型手法：把"设计产能"当成"实际损失"（沙特管道 700 万桶/日）、把"政治宣言"说成"宣布公投"（英国三地区峰会）、把"紧随其后的另一列车"说成"当事人所乘列车"（约翰逊）。

## LLM 集成：抓取 → 总结 Pipeline

twitter-cli **只负责抓取，不做总结**。常见 Agent 工作流是两步走：

```bash
# step 1: 抓取结构化数据
python tw_run.py user-posts @username -n 20 --yaml

# step 2: 把输出喂给 LLM，prompt 例："根据以下推文，总结这个人最近在关注什么话题"
```

> ⚠️ **区分清楚：**
> - **X Premium 内置 "Summarize" 按钮** — X 官方 UI 功能（Grok 驱动），仅限 x.com/app，无法通过 CLI 调用。
> - **xAI Grok API** — 独立 LLM API（`api.x.ai`），可用于第 2 步总结，需额外配 key。
> - **本 skill 定位** — 只提供第 1 步抓取能力，总结层复用宿主已配置的任何模型。`--yaml`/`--json` 就是为这个 pipeline 设计的。

## 🚨 附录：Cookie 失效期的应急通道 — guest token 匿名读单条（2026-10-03 实测）

**触发条件**：`twitter status` 报未认证 / `feed`、`tweet` 全部 401·403，`.env` 里 `auth_token`/`ct0` 已过期，
但你**只需要读 1~2 条公开推文**（正文+点赞/转推数），等重新登录拿 Cookie 太慢。

**能力边界（先想清楚再用）**：仅单条只读。搜索/时间线/回复/用户资料 guest 模式**一律不支持**，
view_count 恒为 0。超过两条以上的需求或要评论区 → 还是去续 Cookie / x_search。

**三步机制**（来源 NewsCrawler twitter_client.py 的实现思路，已在真机验证）：
1. `POST https://api.x.com/1.1/guest/activate.json`，头带公开 Bearer token → 拿 `guest_token`
2. `GET https://x.com/i/api/graphql/{QID}/TweetResultByRestId?variables={"tweetId":"..."}&features={...}`
   头带 `x-guest-token`。**精简 features 即可**（7 个开关，不必抄 X 前端的 40+）
3. 判定：`data.tweetResult.result` 存在=成功；**HTTP 200 但 `tweetResult:{}` 空壳 = 推文已删/私密/受限**（不是通道故障，别白重试）

**实测可跑脚本**（依赖仅 `curl_cffi`，系统 Python 已装 0.16.3）：

```python
# -*- coding: utf-8 -*-
import json, sys
from curl_cffi import requests as cr
BEARER = "AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA"
QID = "Xl5pC_lBk_gcO2ItU39DQw"   # TweetResultByRestId, 会随 X 改版腐烂, 见文末
FEAT = {"longform_notetweets_consumption_enabled": True,
        "responsive_web_text_conversations_enabled": False,
        "view_counts_everywhere_api_enabled": True,
        "bm_organization_read_only_enabled": True,
        "responsive_web_graphql_exclude_directive_enabled": True,
        "verified_phone_label_enabled": False,
        "responsive_web_graphql_skip_user_profile_image_extensions_enabled": False}
tid = sys.argv[1]
gt = cr.post("https://api.x.com/1.1/guest/activate.json",
             headers={"authorization": f"Bearer {BEARER}"}, impersonate="chrome", timeout=15).json()["guest_token"]
d = cr.get(f"https://x.com/i/api/graphql/{QID}/TweetResultByRestId",
           params={"variables": json.dumps({"tweetId": tid, "withCommunity": False,
                    "includePromotedContent": False, "withVoice": False}, separators=(",", ":")),
                   "features": json.dumps(FEAT, separators=(",", ":"))},
           headers={"authorization": f"Bearer {BEARER}", "x-guest-token": gt},
           impersonate="chrome", timeout=15).json()
res = (d.get("data") or {}).get("tweetResult", {}).get("result")
if not res:
    print("EMPTY-SHELL: 推文已删/私密/受限 (HTTP200 空壳, 非通道故障)"); sys.exit(1)
leg = res["legacy"]; usr = res["core"]["user_results"]["result"]["legacy"]
print("@%s | %s" % (usr.get("screen_name"), leg["full_text"][:100]))
print("likes=%s rts=%s created=%s" % (leg.get("favorite_count"), leg.get("retweet_count"), leg.get("created_at")))
```

实测通过：`python gt.py 20` → `@jack | just setting up my twttr, likes=311004`（走本机 10809 代理，~3s/条）。

**两个已踩的坑（勿再试错）**：
- ❌ **纯标准库 urllib 版走不通**：`activate.json` 直接 404——X 对 `api.x.com` 也卡 TLS 指纹，
  **必须 curl_cffi `impersonate="chrome"`**（和微信直链一个病根，同剂药方）。
- ❌ **PowerShell 裸拼 JSON 参数会毁引号**：`--data-urlencode "variables={...}"` 到服务端报
  `variables could not be decoded`；`@file` 形式在 curl.exe 下也没展开（实测发出去的是字面路径）。
  要用 curl.exe 兜底就整段 URL 预编码好传入，否则直接用上面的 Python。

**腐烂预警**：`BEARER` 是 X 网页版公开 token（多年未换，短期安全）；`QID` 是硬编码 queryId，
X 改版会失效——症状是 404/`Feature not found`。届时从浏览器 x.com 的 JS 里重新抓 queryId，
或参考 twitter-cli 的 stale-fallback 机制（社区 live queryId 表）。
guest 通道挂了 ≠ 主通道挂了，修 Cookie 走 twitter-cli 仍是正路。
