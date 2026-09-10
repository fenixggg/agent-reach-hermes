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

### ② `xhs comments` 全线不可用（平台侧，非版本问题）
```
API error: {"code": -1, "success": false}
```
已实测：v0.6.4 与降级 v0.3.5 **两个版本、四种调用方式（裸 id / 全 URL / --xsec-token / --all）全部失败**。命令会返回 `ok: false` 但 exit 0，**脚本里必须检查 `ok` 字段**，否则会误以为"0 条评论"。
→ **采集评论目前走不通**，能做舆情分析的数据只有：笔记标题 + desc 全文 + 互动数（赞/藏/评条数/转发）。

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

## 已知不稳定的命令（v0.6.4）

```bash
# 以下命令当前可能返回 API error，谨慎使用：
xhs user USER_ID          # 可能返回 {code: -1}
xhs user-posts USER_ID    # 可能返回 {code: -1}
xhs favorites              # 可能返回 API error
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
> **POST 操作风险**: 发帖(post)、评论(comment)、点赞(like) 等写操作在 v0.6.x 可能因签名问题返回 406。如需使用，建议降级到 v0.3.5 (`pipx install xiaohongshu-cli==0.3.5`)。
