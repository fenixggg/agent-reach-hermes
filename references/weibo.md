# 微博 / Weibo (weibo-cli + s_weibo_search.py)

> 微博内容双引擎：**weibo-cli**（kabi-weibo-cli v0.2.1，uv tool 安装）负责热搜/详情/评论/用户，**s_weibo_search.py**（本 skill 自带脚本）负责关键词搜索。
> 凭证：`~/.config/weibo-cli/credential.json`（SUB/SUBP cookie，2026-09-08 手动配置）。
>
> ⚠️ **最高频踩坑：帖子链接必须双段 `weibo.com/<uid>/<mid>`**，纯 mid 链接打不开。详细纠正规则见下方「生成帖子链接的强制规则」章节——写报告前必读。

## 安装与登录（2026-09-08 已配置，重装/迁移时按此流程）

```bash
uv tool install kabi-weibo-cli    # 安装（PyPI 包名 kabi-weibo-cli，命令名 weibo）
weibo login --qrcode              # 方式1: 终端二维码，微博App扫码（约3分钟窗口）
weibo login --cookie-source edge  # 方式2: 浏览器提取（⚠️ 本机 Edge 开了 App-Bound Encryption，会失败！）
weibo status                      # 验证
```

> ⚠️ **本机 Edge 有 App-Bound Encryption（同 Reddit 坑）**，浏览器提取路径不可用。实际生效方式：浏览器登录 weibo.com → F12 → Application → Cookies → 复制 `SUB` 和 `SUBP`（必需）→ 手工写入 `~/.config/weibo-cli/credential.json`，格式 `{"cookies": {"SUB": "...", "SUBP": "..."}, "saved_at": <unix_ts>}`。
> 凭证 7 天 TTL，过期自动尝试浏览器重提取（本机会失败）→ 失效时按上面手动方式重新写入。

## 凭证存放位置（2026-09-08 现状）

| 位置 | 说明 |
|---|---|
| `~/.config/weibo-cli/credential.json`（即 `~/.config/weibo-cli/`） | **CLI 实际读取的**，`{"cookies": {"SUB","SUBP"}, "saved_at"}` |
| profile `.env` | 无条目（SUB cookie 无内嵌过期，服务器端实际有效期通常 30 天以上；CLI 内置的 7 天 TTL 只是"建议刷新间隔"，过期后 API 仍可用则继续用）。如需备份可加 `WEIBO_SUB` |

## 能力矩阵（实测）

| 功能 | 工具 | 状态 |
|---|---|---|
| 热搜榜 | `weibo hot --count 10` | ✅ 免登录也可用 |
| 关键词搜索 | **`s_weibo_search.py`** | ✅ 实测 22 条真实结果 |
| 微博详情 | `weibo detail <mid>` | ✅ 完整正文+统计 |
| 评论 | `weibo comments <mid> --count 10` | ✅ |
| 转发 | `weibo reposts <mid>` | ✅ |
| 用户资料/微博列表/关注/粉丝 | `weibo profile/posts/... <uid>` | ✅ |
| 热门时间线 | `weibo feed` | ✅ |
| 关注者时间线 | `weibo home` | 需登录（已配置） |

## 命令速查

```bash
# 热搜榜（⚠️ realtime 条目只有 word/num，没有 mid/uid——要出链接必须用 --resolve-hot 二次解析）
weibo hot --count 10
# 热搜词 → 对应帖子链接（按互动数取最优帖）【热搜出链接的唯一正确方式】
python <skill-path>/scripts/s_weibo_search.py --resolve-hot "热搜词"
# 关键词搜索（⚠️ 不用 weibo search，其移动API与SUB cookie不兼容返回ok=-100）
python <skill-path>/scripts/s_weibo_search.py "关键词" 1
# 读单条微博全文（mid 从搜索结果的 url 或 hot 里拿）
weibo detail <mid> --json
# 评论 / 转发
weibo comments <mid> --count 10
weibo reposts <mid> --count 5
# 用户
weibo profile <uid> --json
weibo posts <uid> --count 10
# 热门时间线
weibo feed --count 10
```

### 各命令返回里的链接要素（生成双段 URL 用）

| 命令 | 返回里有什么 | 出链接方式 |
|---|---|---|
| `s_weibo_search.py` | `uid` + `mid` + 现成的双段 `url` | ✅ 直接用 `url` 字段 |
| `weibo feed` | `statuses[].user.idstr` + `mblogid`/`idstr` | ✅ 拼 `weibo.com/<user.idstr>/<mblogid>` |
| `weibo detail <mid>` | `user.idstr` + `mblogid` | ✅ 同上 |
| `weibo hot` | **只有 word/num，无 mid/uid** | ⚠️ 必须跑 `--resolve-hot "<热搜词>"` 二次解析 |
| `weibo comments/reposts` | 挂在已知 mid 下 | 不需要出链接 |
| **自建采集管线**（直接打 hot_band 等 AJAX API） | **只有 mid，无 uid** | ⚠️ 报告定稿前必须跑 `--fix-links "<mid1>,<mid2>,..."` 补 uid |

## 🔗 链接策略：热点话题优先跳话题聚合页（用户偏好，强制级）

**核心原则：热点话题类内容，报告里的跳转链接用话题聚合页而非单帖**——单帖只见一个人的观点，话题页能看到全网讨论全貌。

```python
# --resolve-hot 输出已含 topic_url 字段（实测可打开，22张卡片聚合全部讨论）:
#   {"url": "https://weibo.com/<uid>/<mid>",          # 互动最高单帖（作为"代表帖"备用）
#    "topic_url": "https://s.weibo.com/weibo?q=<热搜词urlencode>",  # ✅ 话题聚合页,报告主链接用这个
#    ...}
```

**链接选择优先级**：

1. **热点话题/热搜事件** → 用 `topic_url`（`s.weibo.com/weibo?q=<热搜词>` 聚合页，22+ 张卡片，含全部大V和路人讨论）
2. **引用某个具体观点/数据**（"某某博主说…"）→ 用该博主的单帖双段 `url`
3. **普通关键词搜索的列表呈现** → 每条用各自的单帖 `url`
4. 兜底：`m.weibo.cn/status/<mid>`（手机版兼容）

**实施记录**：`resolve_hot()` 已返回 `topic_url` 字段；话题聚合页实测无登录墙（带不带#号均可，带#号结果更全）。

## 📊 热搜接口实测（2026-09-10，本会话探测结论）

| 端点 | 结果 |
|---|---|
| `GET https://weibo.com/ajax/statuses/hot_band` | ✅ 返回 `band_list`（52 条），**每条带 `category` 字段**（数码/民生新闻/艺人/剧集/体育/综艺/海外新闻/财经/互联网/舆论监督/美食/幽默/情感…），另有 `num`（热度值）、`realpos`、`onboard_time`（上榜时间戳）、`subject_querys`（关联事件） |
| `?band_id=1/2/3…/102803/10003/20036/60011/80011` | ❌ **band_id 被服务端忽略**，全部返回同一份实时热搜榜 |
| `GET https://weibo.com/ajax/side/hotSearch?cate=finance\|news\|ent\|social\|stock` | ❌ **cate 参数无效**，只改第 5 位广告位 |
| `GET https://s.weibo.com/top/summary?cate=finance\|news\|ent\|social\|stock` | ❌ 同上，榜单主体不变 |
| `GET https://weibo.com/ajax/statuses/show?id=<mblogid>` | ✅ 单帖元数据（`user.idstr` / `text_raw` / `screen_name`）—— **L3 指向校验的唯一可信接口** |

**三条硬结论**：

1. **微博没有可用的分类热搜榜**（财经/AI/国际都没有）。`hotSearch?cate=` / `band_id` / `s.weibo.com/top/summary?cate=` 全部被忽略，返回的都是同一份实时榜。
2. **任何专题热点（财经/AI/国际…）在实时榜里占比极低甚至为 0**。实测同日：财经类 52 条中仅 1 条（`category=财经`）；国际类仅 3 条（全是「日本梅毒疫情」）；AI 类 0 条（数码/互联网 13 条全是 iPhone/华为/vivo 消费电子）。
   → **专题报告必须走关键词搜索池**：`s_weibo_search.py` 批量搜该领域关键词（每词 15–25 条），再用跨关键词正则命中统计排序，**不要指望榜单**。
3. **榜单广告位条目要剔除**：特征为 `is_ad:1` + `small_icon_desc:"商"`（如「花呗官宣天猫买新iPhone24期免息」），它们会挤进真实榜单排名。

## ⚠️ 生成帖子链接的强制规则（单帖链接的自动纠正，agent 必读）

**微博帖子 URL 只有双段格式才有效**（热点话题主链接用上面的话题聚合页，以下规则管单帖链接）：

```
✅ https://weibo.com/<作者UID>/<mid>     例: https://weibo.com/1744332207/5341282423800693
❌ https://weibo.com/<mid>              纯mid单段: 未登录302跳passport.visitor报错页, 登录态也常进不了帖子
```

**Agent 写报告/输出链接时的自动纠正规则**：

1. `s_weibo_search.py` 的输出已含正确双段 `url` 和独立 `uid`/`mid` 字段——**直接用它的 `url` 字段，不要自己拼**。
2. 如果数据源只有 mid（如 `weibo detail` 的返回），**必须先拿到作者 uid** 才能生成链接：
   - `weibo detail <mid> --json` 返回里的 `user.idstr` 就是 uid；
   - 拼成 `https://weibo.com/<uid>/<mid>`。
3. **如果数据源来自 `weibo hot`**（其返回只有热搜词，无任何 mid/uid）——**禁止用词句直接造链接**，必须跑：
   ```bash
   python <skill-path>/scripts/s_weibo_search.py --resolve-hot "<热搜词>"
   ```
   返回该词下互动数最高的帖子的 uid/mid/双段 URL。
4. 自检正则：生成的链接若不匹配 `weibo\.com/\d{6,}/[A-Za-z0-9]+`（斜杠后第一段必须是 6 位以上纯数字 uid），即为错误格式，重新取 uid 修正后再输出。
5. 实在拿不到 uid 的兜底：用 `https://m.weibo.cn/status/<mid>`（手机版兼容单 mid）。
6. 验证方法（如需确认）：带登录 cookie 请求双段 URL 应 HTTP 200；单段 URL 会 302 到 `passport.weibo.com/visitor/...`。

**踩坑记录**：2026-09-10 的微博财经日报和 AI 热点两份 HTML 报告都因用单段 mid 链接全部打不开（AI 报告是二次踩坑——数据源来自 weibo hot，agent 未做 resolve 直接拼了 mid）。此规则为强制级，覆盖任何"简洁链接"的倾向。**weibo hot 场景必须走 --resolve-hot**。

**第三次踩坑（2026-09-10 下午，另一会话）**：agent 绕开脚本自建采集管线（直接打 hot_band AJAX API），hot_band 返回只有 mid 没有 uid → 报告又全是单段链接。教训：**无论数据来自哪条路，报告定稿前必须跑一次链接修补**：

```bash
# 把报告里所有单段 mid 喂进去（逗号分隔），自动补 uid 出双段链接+作者+正文核对
python <skill-path>/scripts/s_weibo_search.py --fix-links "<mid1>,<mid2>,..."
```

输出含 `mid/uid/author/url(双段)/m_url(手机版兜底)/text(正文前200字, 可核对与标题是否同题)`。**这是任何微博采集流程的最后一道工序，等价于"链接 lint"**。

**第四次踩坑（2026-09-10 傍晚，本会话复核）**：另一会话"修链接"时把 intl 报告三条标题链接批量替换成了**未核对内容**的双段 URL —— 结果 TOP 1「美加贸易战」的链接指向的是**青松古藤的"央行增持黄金"帖**。链接格式全对、HTTP 200，但**内容完全不对题**。用 `ajax/statuses/show?id=<mblogid>` 反查才发现。

> **只校验格式是不够的，必须校验指向。** 双段链接的陷阱在于：uid 和 mblogid 一旦错配（或从别的报告复制粘贴），格式正则照样通过。
>

## ✅ 链路校验的三层（缺一层都可能出错，2026-09-10 定稿规则）

| 层 | 检查什么 | 方法 | 判据 |
|---|---|---|---|
| L1 格式 | 是否双段 `weibo.com/<uid>/<mid>` | 正则 `weibo\.com/\d{6,}/[A-Za-z0-9]+` | 单段必错 |
| L2 可达 | 能否打开 | 带 cookie 请求 | **⚠️ 不可靠**：双段返回 SPA 壳(200/7KB)、单段返回 404 页(200/961B)，都是 200 但网页真伪不同 |
| L3 指向 | **是否是该议题的帖子** | `GET https://weibo.com/ajax/statuses/show?id=<mblogid>` → 核对 `user.idstr` + `text_raw` | **唯一可信的校验** |

**推荐做法（最省事且最稳）：热点话题类报告直接用话题聚合页 `s.weibo.com/weibo?q=<词>` 作主链接**，绕开整个 uid/mblogid 配对问题——实测返回 300KB+ 真实卡片，无登录墙，且比单帖更全面（用户偏好也是这个）。只有"引用某个博主的具体观点"时才用单帖双段链接，且**必须跑 L3 反查核对**。

**双段链接的错误风险高发场景**：跨报告批量修链接（多个会话/多份报告并行时，URL 极易串）。本会话四份报告（财经 Top5 / AI Top3 / 国际 Top3 / 国外AI Top3）就是教训。

## 已知坑

- **帖子 URL 必须双段格式 `https://weibo.com/<uid>/<mid>`**：s.weibo.com 搜索页的 action-data 里带作者 uid。纯 mid 单段链接（`weibo.com/5341...`）未登录时会 302 跳 passport.visitor 报错、登录态下也常进不了帖子页——脚本已修复（2026-09-10），提取 uid 拼双段 URL，uid 缺失时降级用 `m.weibo.cn/status/<mid>`。
- **`weibo search` 不可用**：其走 `m.weibo.cn/api/container/getIndex` 移动API，对 SUB cookie 返回 `ok=-100`（会话无效）。搜索一律用本 skill 的 `s_weibo_search.py`（解析 s.weibo.com 网页版，实测稳定）。
- **`weibo login --cookie-source edge` 不可用**：Edge App-Bound Encryption，RequiresAdminError。手动写 credential.json。
- **凭证 7 天 TTL 是 CLI 自己的"建议刷新间隔"**：SUB cookie 本身无内嵌过期（非 JWT），服务器端实际有效期通常 30 天以上。TTL 到期后 CLI 会尝试浏览器刷新（本机会失败）并警告 "using existing cookies"——**只要 API 不返回 ok=-100 就继续用**。真正失效场景：改密码、其他设备登录顶号、风控踢、长期不用。失效后重新 F12 复制 SUB/SUBP 写入 credential.json。
- **输出**：非 TTY 默认 YAML；需要 JSON 加 `--json`。
