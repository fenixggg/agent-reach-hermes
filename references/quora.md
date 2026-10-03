# Quora 问答提取 (s_quora.py)

> 状态：**✅ 可用（2026-10-03 建成并实测）**。答案页 / 问题页双形态，输出结构化 JSON/Markdown。
> 原理：**Firecrawl 浏览器渲染 + 本地 Markdown 答案切割器**。Quora 是零 HTTP 路线被证实全灭的站点，这是唯一通路。

## 1. 快速使用

```bash
# 单答案页(推荐,内容最完整): /answer/ 永久链接
python <skill-path>/scripts/s_quora.py "https://www.quora.com/<Question-slug>/answer/<User-slug>"

# 问题页多答案(默认最多8条, --limit 控制)
python <skill-path>/scripts/s_quora.py "https://www.quora.com/<Question-slug>" --limit 5

# 纯 Markdown / 落盘 / 高级参数
python <skill-path>/scripts/s_quora.py "URL" --format md
python <skill-path>/scripts/s_quora.py "URL" --save-to out.json   # utf-8 无BOM
python <skill-path>/scripts/s_quora.py "URL" --wait 9000          # 渲染等待ms(默认7000)
python <skill-path>/scripts/s_quora.py "URL" --cookie-file q.txt  # 可选:登录Cookie(每行 name=value)
```

JSON 信封字段：`title / mode(answer|question) / n_answers / answers[]`，每条答案含
`author / credentials(凭据线) / time_ago / upvotes / views / original_question(转引) / text(纯文) / with_images(保留图片序) / images[] / cr_deduped`。

## 2. 为什么走浏览器渲染（零 HTTP 路线排查记录，2026-10-03，勿重复试错）

| 路线 | 结果 |
|---|---|
| curl_cffi impersonate=chrome 直请 www/m./带Referer | ❌ Cloudflare "Just a moment" 403 |
| RSS (rss-feed/)、embed/oembed 端点 | ❌ 全部 CF 403 |
| GraphQL POST（gql_pars / graphql/gql，匿名） | ❌ CF 403（GET 405 只是换姿势死） |
| api.quora.com 老 REST API | ⚠️ 域名活着(无CF)，但答案/问题端点全 404——API 已废弃 |
| Quetre 前端实例（quetre.iket.me 等） | ❌ 问题页 503 / 搜索 410 / 只剩 About 页，公共实例死光 |
| 浏览器登录 Cookie 偷取(Edge DB) | ❌ Edge 127+ 独占锁 + App-Bound 加密，进程读不走 |
| NewsCrawler quora.py 移植 | ❌ 解析的 `push("{\"data\":{\"answer\"...)` 数据块已被 Quora 改版下线（页面探针 0 命中），新版是 `ansFrontendGlobals.data.inlineQueryResults` |
| **Firecrawl v2 scrape(本方案)** | ✅ ~10s，渲染后 DOM 完整；托管浏览器同页实测可开 |

**结论**：Quora 数据只存在于渲染后的 DOM；`s_quora.py` 直调 Firecrawl API（纯标准库 urllib，绕开 CLI 的 axios 代理 bug），把渲染 Markdown 切成结构化答案。

## 3. 成本与纪律

- **每次调用烧 1 Firecrawl scrape 积分**。Quora 渠道专用——其它站点照旧先 better-webfetch。
- **评论区拿不到**（2026-10-03 实测）：答案的评论折叠在"View comments"按钮后，展开需要浏览器交互
  （Firecrawl `actions`），但该特性**按地区封锁**——本账号(中国出口)调用返回 403
  `Use of headers, actions...not allowed by default in your country`。想补评论需 Firecrawl 官方开白
  或托管浏览器逐条展开（成本远超 1 积分，不值）。答案正文里的社区互动已包含在文本中。
- 问题页长答案有「预览→Continue Reading→全文」折叠渲染，脚本已自动去重（保留全文删预览）；
  若要某人的完整长答案，**优先用 /answer/ 永久链接**（答案页形态渲染最干净）。
- `waitFor` 默认 7000ms，空壳自动升档重试一次；还失败基本是内容被删/私密。
- 浏览量(view count)只在答案页形态可得；问题页给的是 upvote 数。
- 渲染页自带「相关问题卡 / Hottie 侧栏 / +10 折叠计数」尾巴混进答案正文的噪声，已进
  NOISE_LINE_PATTERNS 黑名单；新形态噪声按行补进脚本即可。

## 4. 找 Quora URL

- 搜索：走 10r_search / tavily `site:quora.com` 过滤（X 无趋势接口同理，用搜索代替站内导航）
- 答案页链接形态：`quora.com/<问题slug>/answer/<人名slug>`；问题页：`quora.com/<问题slug>`
- ⚠️ detector 老坑回顾：NewsCrawler 的 quora 规则只匹配答案页结构——我们两形态都支持。

## 凭证存放位置

Firecrawl key 沿用现有体系：Hermes profile `.env` → `~/.hermes/.env`（`FIRECRAWL_API_KEY=`），
脚本自动按此顺序读取，也可环境变量直给。无 Quora 账号凭证；`--cookie-file` 可选传你手动导出的
quora.com Cookie（仅长文被折叠时提升完整度用，一般不需要）。Cookie 文件放 `~/.agent-reach/`，勿入库。

## 故障速查

| 症状 | 原因 | 处置 |
|---|---|---|
| `Firecrawl HTTP 402` | 积分耗尽 | 等月度重置或换 key |
| `页面未渲染出答案结构` | 登录墙内容/已删/CF 间歇拦截 | 换 /answer/ 链接、加大 --wait 重试一次 |
| `FIRECRAWL_API_KEY 未找到` | 两处 .env 都缺 key | 补 .env |
| 正文尾部偶现 `2K`/`More` 小按钮文本 | 渲染态差异 | 已进噪音黑名单；若复发按行加入 NOISE_LINE_PATTERNS |
