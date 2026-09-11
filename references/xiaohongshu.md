# 小红书 / XiaoHongShu (xhs-cli)

## 安装与登录（2026-09-08 已配置，重装/迁移时按此流程）

```bash
pipx install xiaohongshu-cli    # 安装
xhs login                       # 自动从浏览器提取 Cookie（需浏览器已登录小红书）
```

> Cookie 落盘 `~/.xiaohongshu-cli/cookies.json`（位置详情见下方凭证章节）。

## 稳定可用的命令

```bash
# 搜索笔记（推荐入口）
xhs search "query"

# 阅读笔记详情（必须用搜索结果中的 URL 或 ID，不能裸 note_id）
xhs read NOTE_ID_OR_URL

# 查看评论
xhs comments NOTE_ID_OR_URL

# 浏览热门
xhs hot

# 推荐 feed
xhs feed
```

## v0.6.4 实测坑（2026-09-10 采集小米澎程时踩到，新增）

### ① 笔记链接必须带 `xsec_token`，否则全是同一张空壳页
```bash
# ❌ 不带 token: 三条不同笔记返回的都是同一份 96365 字节通用页, 页面内无笔记标题
https://www.xiaohongshu.com/explore/<note_id>
# ✅ 带 token: 各自返回 66-70KB 真实内容, 含笔记标题
https://www.xiaohongshu.com/explore/<note_id>?xsec_token=<token>&xsec_source=pc_search
```
**token 来源**：`xhs search --json` 返回的每条 item 里的 `xsec_token` 字段（注意：笔记的 `xsec_token` 在 item 顶层，用户头像旁的那个是**用户** token，两者不通用）。
**判定方法**：多个不同 note_id 若返回**相同字节数**，即为无 token 的兜底页。

### ② `xhs comments` 返回 `code: -1` / HTTP 406 —— **根因是 xhshow 依赖过旧，升级即修复（2026-09-11 已解决）**

```
❌ 症状：命令返回 ok:false + {"code": -1, "success": false}（exit 0，脚本须查 ok 字段）
   -v 调试可见真实错误：GET edith.xiaohongshu.com/api/sns/web/v2/comment/page
   → HTTP 406 Not Acceptable
   响应头 Access-Control-Allow-Headers: f,x-s,x-sign,x-t 说明是「签名校验」被拒
```

**根因**：签名由 `xhshow` 库生成，其内部硬编码 `DATA_SDK_VERSION = "4.2.6"`（写进 x-s / x-s-common 头）。小红书轮换了服务端可接受的客户端版本，旧版 xhshow（0.1.9）的签名被 WAF 以 406 拒绝。

**关键鉴别**：`xhs search` / `read` / `feed` / `hot` 全部正常 → **说明 cookie 有效、签名机制没坏，只有 comment 端点额外校验了 SDK 版本**。别误判成「账号被封」或「平台彻底废除接口」（这正是 2026-09-10 的错误结论，当时误把「依赖库版本滞后」当成「平台侧失败」）。

**修复（一条命令）**：
```bash
# xhs-cli venv 在 <pipx-venv-path>/xiaohongshu-cli
$env:PATH = "<pipx-venv-path>/xiaohongshu-cli\Scripts;" + $env:PATH
python -m pip install --upgrade "xhshow==0.2.0"   # 0.1.9 → 0.2.0
# 验证：xhs comments <带xsec_token的URL> --json → ok:true
```
> ⚠️ `pipx upgrade xiaohongshu-cli` **无效**——xiaohongshu-cli 0.6.4 已是 PyPI 最新版，且只锁 `xhshow>=`，不会主动拉新版依赖。必须手动升级 xhshow。

**修复后能力**（2026-09-11 实测）：
- `xhs comments <URL> --json`：返回顶层评论 + 内嵌 `sub_comments` 子评论 + `like_count` / `sub_comment_count` / `ip_location` / `create_time`
- `--all`：自动翻页（**但有硬上限，见下**）
- 评论正文在 `content` 字段；作者昵称在 `user_info.nickname`
- ⚠️ 首屏会内联带上若干条子评论（`sub_comments`），做统计时注意去重

### ②-b ⚠️ `--all` 不是「全部」——有 200 条硬上限（2026-09-11 压测实测）

53 条笔记批量压测（评论数均 ≥30）结论：

| 声明评论数区间 | 笔记数 | 覆盖率（实得/声明） |
|---|---|---|
| 0–40 | 8 | 51.2% |
| 40–80 | 23 | 49.6% |
| 80–150 | 11 | 43.7% |
| **150+** | 11 | **28.3%** |

- **单帖实得上限 = 200 条**（实测：官方发布帖声明 1493 条，`--all` 只返回**恰好 200** 条）
- **覆盖率随笔记热度单调递减**：小帖约一半，超热帖仅约 1/4
- 53/53 全部 `ok:true`，**零失败、无限流**（平均 7.9s/帖，间隔 3s）

**结论**：`--all` 拿的是「热门切片」而非全量——**按热度排序的前 200 条左右**，实际是**按点赞/权重排序的头部评论**。做舆情分析时：
- ✅ 可用：抓高频共识、代表性观点（头部评论恰恰是最有信息量的）
- ❌ 不可用：声称「抓了全部评论」、做精确的百分比统计（分母不可信）
- 📌 出报告必须标注「样本为头部截面，非全量」，与头条评论接口的「累计池」问题同类

> 若确需全量：手动用 `--cursor` 逐页翻（`get_all_comments` 源码里有 `max_pages=20` 上限），或直接调用底层 `comment/page` 接口自行分页。

### ②-c ⚠️ 昵称统计陷阱：`momo` 是默认昵称（务必用 user_id 统计）

实测 3228 条评论中，昵称为 `momo` 的 **193 条来自 161 个不同 `user_id`**。
→ **统计「谁发言最多」必须用 `user_id`**，按 `author` 昵称聚合会得出完全错误的结论。
→ 同类默认昵称还有：`用户已注销`、`小红薯` 等。分析前先做「同昵称多 user_id」检测。

### ②-d ⚠️ 评论时序陷阱：高赞 ≠ 本次事件（做发布类舆情必读）

**问题**：笔记评论区是**累积池**——一条笔记发布后评论持续累积数周甚至数月。`--all` 按热度返回的头部评论，**大量产生于你要分析的事件之前**。

**实测（V4.1 Flash 发布舆情）**：Top 40 高赞评论中 **23 条来自发布前**（最高赞 3969 那条写于发布前 5 天），仅 17 条来自发布日。
→ 不看 `create_time` 就会把「笔记长期积累的社区共识」误当成「对本次发布的即时反应」。**这是归因错误。**

**正确做法**：
```python
# 1) 先按事件窗口过滤，再取高赞（不要先取头部再看时间）
from datetime import datetime, timezone, timedelta
CST = timezone(timedelta(hours=8))
dt = datetime.fromtimestamp(int(create_time)/1000, CST)
win = [r for r in rows if '2026-09-10' <= dt.strftime('%Y-%m-%d') <= '2026-09-11']
# 2) 报告必须分时段汇报，并列明「高赞来自发布前的比例」
```

**反直觉发现**：负面率在「内测期/发布日/次日」高度稳定（8%/8%/9%）——
→ **负面情绪未必是「发布后爆发」，可能是贯穿周期的基础盘**。不分时段就下「发布后口碑恶化」的结论是危险的。

### ②-e ⚠️ 按互动量筛样本会漏掉「低互动高信息量」的帖

实测教训：筛选条件设为「评论数 ≥30」时，漏掉了标题即负面的帖（如「DeepSeek V4.1 flash极不稳定」仅 23 条评论），而里面有一条 **43 赞的高信息密度证词**（「燒 token 更快更貴，重點是更笨，連圖片識別常常出包」），信息量超过多数高互动帖。

→ **采集时应按标题极性做一次补充采样**（负面/质疑词命中），而非只按互动量。低互动 ≠ 低价值。

### ③ `search` 与 `read` 的互动数精度不同（出报告必用 read 值）
| 来源 | liked_count 示例 | 说明 |
|---|---|---|
| `xhs search --json` | `"24523"` | 数字串，但**是快照、会失真** |
| `xhs read --json` | `"2.5万"` / `"10万+"` | **官方展示值**（可能是高精度后的取整） |

实测同一笔记：search 给 `103153`，read 给 `10万+`；另一条 search 给 `24523`、read 给 `2.5万`。
→ 报告写"10万+赞"用 read 值更稳妥；**需要精确排序时用 search 的原始数字串**。
→ 另外：`read` 的 `interact_info` 里转发字段名叫 **`share_count`**，而 `search` 里叫 **`shared_count`**，写解析代码时注意别漏。

### ④ 正文大面积为空是常态（不要当成采集失败）
视频笔记普遍不写文字。实测 172 条笔记中 **35% 的 desc 为空或仅含话题标签**。
→ 情感分析/议题分类会因此**系统性低估负面**（空文本全落入"中性"）。出报告时必须显式标注这个偏差。

### ⑤ 高频话题标签可用于识别官方营销投放
同一 campaign 的自定义标签（如本次的 `#智能可变大空间SUV#` 9 条、`#小米澎程第N空间#` 7 条）覆盖多条高互动笔记，是**官方话题驱动 + KOC 协同**的间接证据。
另一个信号：**转发数 > 点赞数**（正常内容通常 1:10~1:50）。实测 4 条笔记是 1.8–2.9 倍，通常意味着进入了分享激励/话题活动分发。**这是推断，不是证实**——小红书不强制标注广告。

### ⑥ `read --json` 的真实结构：正文/互动数在 `data.items[0].note_card`（2026-09-11 实测）

`xhs read URL --json` 返回的是**列表结构**，不是单条 note_card：
```python
d = json.loads(out)
nc = d['data']['items'][0]['note_card']   # ✅ 正确
# ❌ 错误：d['data']['note_card'] —— 不存在，会拿到空值
```
`note_card` 内字段：`title`（**注意不是 `display_title`**）、`desc`（正文全文）、
`interact_info`（`liked_count` / `collected_count` / `comment_count` / `share_count`）、
`user.nickname`、`time`（毫秒时间戳）、`ip_location`、`tag_list`、`at_user_list`。
→ 若解析拿到的 title/desc/like 全空，**99% 是取错层级，不是采集失败**。

### ⑦ 批量子进程调用：必须清 `PYTHONPATH` + 不要用 PS 重定向（2026-09-11 实测）

- 用 Python `subprocess.run(['xhs', ...], env=env)` 批量读笔记时，`env` 必须显式清空
  `PYTHONPATH`（`env['PYTHONPATH'] = ''`），否则 click/ctypes 模块冲突。
- ❌ PowerShell 的 `xhs read ... --json > file.json` 会写成 **UTF-16**（读到 `0xff` BOM 报
  `UnicodeDecodeError`）；`| Out-File -Encoding utf8` 则带 BOM，需按 `utf-8-sig` 读。
- ✅ 最稳做法：全部走 `subprocess.run(capture_output=True)` + 内存
  `json.loads(p.stdout.decode('utf-8'))`，不落中间文件。
- 频率：每条 `read` 间隔 2.5s，实测 47 条无验证码，全程约 2–3 分钟，适合后台跑。

## 已知不稳定 / 需注意的命令（v0.6.4）

```bash
# ⚠️ 以下三个命令 2026-09-10 曾报 {code: -1}，2026-09-11 升级 xhshow 0.2.0 后实测全部恢复：
xhs user USER_ID          # ✅ ok:true，返回昵称等资料
xhs user-posts USER_ID    # ✅ ok:true
xhs favorites              # ✅ ok:true
# → 结论：这三条当时的失败与 comments 同根因（xhshow 0.1.9 签名被 406 拒），
#   升级依赖后一并修复。若日后再次集体报 -1，优先排查 xhshow 版本，而非怀疑账号/平台。
```

## 凭证存放位置（2026-09-08 实测）

| 项 | 状态 |
|---|---|
| Cookie 文件 | `~/.xiaohongshu-cli/cookies.json`（**CLI 实际读取的**，含 web_session 等 16 个键） |
| .env | 无条目（xhs-cli 只认本地 cookie 文件，无需 env） |
| 当前状态 | ✅ 有效（2026-06-27 更新，实测 `xhs read` 正常返回） |
| 失效恢复 | `xhs login`（自动从浏览器提取 Cookie，需浏览器已登录小红书） |
| 注意 | cookie 含 `web_session` 登录态，**明文文件**，不要复制到别处 |

## 重要注意事项

> **安装**: `pipx install xiaohongshu-cli`，然后 `xhs login`（自动从浏览器提取 Cookie）。
> Cookie 文件路径: `~/.xiaohongshu-cli/cookies.json`
>
> **xsec_token 限制**: 小红书强制 xsec_token 机制，**不能直接用裸 note_id 去读**。正确流程是：先 `xhs search` 或 `xhs feed` 获取结果，再用结果中的 URL/ID 去 `xhs read`。直接构造 note_id 会被拦截。
>
> **频率控制**: 高频请求（批量搜索、深翻评论）会触发验证码，这是平台限制无法绕过。建议每次操作间隔 2-3 秒。
>
> **POST 操作风险**: 发帖(post)、评论(comment)、点赞(like) 等**写操作**在 v0.6.x 可能因签名问题返回 406。
> ⚠️ **不要用「降级到 v0.3.5」来解决**——降级会连带降低 xhshow 依赖，反而可能触发本文档 ② 的同类 406。正确顺序：先 `python -m pip install --upgrade xhshow`（当前已修到 0.2.0），再测。
> 注：写操作涉及真实账号副作用（发帖/点赞），**尚未实测**，以上为推断。
