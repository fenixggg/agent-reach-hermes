# B站 / Bilibili (bilibili-cli)

使用 `bili` 命令（属于 `public-clis/bilibili-cli`，和 xhs-cli / twitter-cli 同一作者）。

## 安装与登录（2026-09-08 已配置，重装/迁移时按此流程）

```bash
uv tool install bilibili-cli
# 或：pipx install bilibili-cli

bili login      # 扫码登录（B站 App 扫）
bili status     # 验证
```

> ⚠️ 扫码确认成功后 B站风控可能不下发 cookie（credential.json 里值全空）。**实际配置方式**：浏览器登录 bilibili.com → F12 → Application → Cookies → 复制 `SESSDATA`/`bili_jct`/`dedeuserid` → 直接改写 `~/.bilibili-cli/credential.json` 对应字段（schema 见下方凭证章节）。
> 大部分读命令免登录（hot/search/video/rank/user/字幕 实测正常）。

## 视频

```bash
# 视频详情（含播放量、点赞、投币、收藏等统计）
bili video BV19xwKeTEye
bili video BV19xwKeTEye --yaml          # Agent 友好结构化输出
bili video BV19xwKeTEye --json          # JSON 格式

# 字幕
bili video BV19xwKeTEye --subtitle      # 纯文本字幕
bili video BV19xwKeTEye --subtitle-timeline     # 带时间线字幕
bili video BV19xwKeTEye -st --subtitle-format srt  # 导出 SRT

# AI 总结 + 评论 + 相关推荐
bili video BV19xwKeTEye --ai            # B站 AI 总结
bili video BV19xwKeTEye --comments      # 热门评论
bili video BV19xwKeTEye --related       # 相关推荐
bili video BV19xwKeTEye --comments --related --json   # 合并输出
```

## 搜索

```bash
# 搜索用户（默认）
bili search "关键词"

# 搜索视频
bili search "关键词" --type video
bili search "关键词" --type video --max 5
```

## 发现

```bash
bili hot                                # 热门视频（第1页）
bili hot --page 2 --max 10              # 翻页
bili rank                               # 全站排行榜（3日）
bili rank --day 7 --max 30              # 7日榜
```

## 用户

```bash
bili user 27534330                      # UP 主资料
bili user "影视飓风"                     # 按用户名搜索
bili user-videos 27534330 --max 20      # 视频列表
```

## 收藏夹与动态

```bash
bili favorites                          # 收藏夹列表（需登录）
bili watch-later                        # 稍后再看
bili history                            # 观看历史
bili feed                               # 动态时间线（需登录）
```

## 互动（需登录）

```bash
bili like BV19xwKeTEye                  # 点赞
bili coin BV19xwKeTEye                  # 投币
bili triple BV19xwKeTEye                # 一键三连
```

## 挖「某条具体爆款视频」：元数据筛选法 ⭐

适用场景：用户只给模糊线索（"B站排名第二""播放600多万""讲年轻人当流浪汉的"），
**不知道标题/UP主/BV号**。关键词搜索在这种任务上几乎必然失败，因为爆款标题常是黑话。

### 为什么关键词搜索会失败（2026-09-10 实战教训）

真实案例：目标是《当你的资产缩水到A0层级，挑选优质桥洞的六大方案！》（手搓工坊M，736万播放，
**B站官方标注「全站排行榜最高第2名」**）。标题里**根本没有"流浪汉"三个字**，
用 `bili search "流浪汉"` / `"流浪汉 教程"` / `"纸板 监控"` 等 27 组关键词全部搜不到。
3 个并行子智能体在此任务上集体给出"该视频不存在"的错误结论——它们只是在错误候选集里反复论证。

> ⚠️ **教训**：给 subagent 的 context 里如果塞了错误的候选清单，它会帮你把错误论证得更完整。
> 这类任务不要用关键词搜索，要用元数据筛选。

### 正确流程

**Step 1 — 广撒网收集 BV 号**（关键词这一步只用来圈定"可能相关"的池子，不要指望命中）

```powershell
# 多关键词 × 翻页，去重收集 bvid
$all=@()
foreach($kw in @("流浪汉","流浪 生存","0元生存","无家可归","桥洞","开宝箱")){
  foreach($p in 1..3){
    $j = bili search "$kw" --type video --max 20 --page $p --json 2>$null | Out-String
    try { $o = $j | ConvertFrom-Json } catch { continue }
    foreach($it in $o.data){ $all += $it.bvid }
  }
}
$all | Select-Object -Unique
```

**Step 2 — 逐个调官方 view 接口，拿「B站官方记录的历史最高排名」**

关键字段 **`stat.his_rank`** = 该视频历史最高全站排名（0 表示没进过榜）。
这是**全网唯一能验证"曾排全站第N"的权威字段**。配合 `pubdate` 卡时间窗、`stat.view` 卡播放量。

```powershell
$ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
$raw = curl.exe -s -H "User-Agent: $ua" -H "Referer: https://www.bilibili.com/" `
       "https://api.bilibili.com/x/web-interface/view?bvid=BV1ZNtA6CExY"
$v = (($raw | Out-String) | ConvertFrom-Json).data
$v.stat.his_rank                  # 2  ← 「全站排行榜最高第2名」
$v.stat.view; $v.stat.like        # 播放/点赞
$v.pubdate                        # unix 秒
$v.honor_reply.honor | % { $_.desc }   # 荣誉标签数组，含"全站排行榜最高第N名"
```

两条判据同时成立即可锁定候选：
- `stat.his_rank == 目标名次`（本例 `=2`）
- `honor_reply.honor` 里出现 `全站排行榜最高第N名` 文本

**Step 3 — 内容级验证（标题对不上时靠这个定案）**

```powershell
# 弹幕（免登录，验关键词最有效）
curl.exe -s -H "User-Agent: $ua" -H "Referer: https://www.bilibili.com/video/BV1ZNtA6CExY/" `
  "https://api.bilibili.com/x/v1/dm/list.so?oid=<CID>"
# ⚠️ 返回是 deflate 压缩，需解压；用 Python urllib 时请求头加 Accept-Encoding 再 zlib.decompress
# ⚠️ 该接口只返回前 ~600 条，对长视频需配合评论一起看

# 评论（分页）
curl.exe -s -H "User-Agent: $ua" "https://api.bilibili.com/x/v2/reply/main?oid=<AID>&type=1&mode=3&ps=20&pn=1"
# AID 从 view 接口的 data.aid 取
```

**Step 4 — 音频转录拿逐字文案（最硬的证据）**

当标题/弹幕仍不能确证内容时，把音频拉下来做 ASR。两步走：

```powershell
# 4a. 取 dash 音频流地址（fnval=16 才返回 dash 结构）
curl.exe -s -H "User-Agent: $ua" -H "Referer: https://www.bilibili.com/" `
  "https://api.bilibili.com/x/player/playurl?bvid=<BV>&cid=<CID>&fnval=16&qn=64&fourk=1"
# 从 data.dash.audio 里挑 bandwidth 最大的，用 baseUrl（失败则用 backupUrl[0]）下载
curl.exe -sL -o audio.m4s -H "User-Agent: $ua" -H "Referer: https://www.bilibili.com/" `
  -H "Origin: https://www.bilibili.com" "<baseUrl>"

# 4b. 转 mp3 → Groq Whisper（key 在 Hermes .env 的 GROQ_API_KEY）
ffmpeg -y -i audio.m4s -vn -ac 1 -ar 16000 -b:a 64k audio.mp3
# 上传 https://api.groq.com/openai/v1/audio/transcriptions  model=whisper-large-v3 language=zh response_format=text
# ⚠️ 本机 python 没装 openai 包 → 用 urllib 手工拼 multipart/form-data，别为了跑一次装包
```

### 坑位清单

| 坑 | 现象 | 解法 |
|---|---|---|
| `bili audio` 失效 | `获取音频流: 'NoneType' object has no attribute 'value'` | 绕开 CLI，直接用 `x/player/playurl` 手拉 dash |
| `yt-dlp` 被拦 | `HTTP Error 412` | B站加大反爬，改用上面的官方 API 路径 |
| UP主视频列表 | `bili user-videos` 返回 title 有值但 owner/stats 全空 | 拿 bvid 再逐个调 `view` 接口补数据；`space/arc/search`（含 wbi 版）已 412/-799 |
| 弹幕乱码 | `'utf-8' codec can't decode byte 0x94` | 响应是 deflate，先解压再 decode |
| PowerShell 脚本中文乱码 | `.ps1` 里中文全部变成 `娴佹氮姹` | PS 5.1 读无 BOM 的 .ps1 会按 GBK 解析 → **复杂中文逻辑改写成 Python 脚本** |
| `python -c "..."` 多行中文 | `ExpressionsMustBeFirstInPipeline` | 同上，写成 .py 文件执行 |

## 认证

```bash
bili status                             # 检查登录状态
bili login                              # 扫码登录
```

大部分读命令无需登录。字幕、收藏夹、动态需要登录。

## 凭证存放位置（最近实测 2026-09-10，源码级诊断）

| 项 | 状态 |
|---|---|
| 登录态文件 | `~/.bilibili-cli/credential.json`（**CLI 实际读取的**，字段：sessdata/bili_jct/ac_time_value/buvid3/buvid4/dedeuserid/saved_at） |
| 当前状态 | ✅ 已登录（2026-09-10 21:54 重配，user: <your_username> Lv4，favorites/history/watch-later 实测全部通过） |
| 重配优先级 | 读类命令免登录，不配也能干活；仅 `favorites`/`watch-later`/`history`/`feed`/`like`/`coin`/`triple` 需要 |
| 过期征兆 | stderr 出现 `bili_cli.auth: Saved credential is expired, clearing` → **文件已被 CLI 静默删除** |

### ⚠️ 为什么会「很快就过期」——TTL 机制 + 静默删文件（2026-09-10 源码级诊断）

读 `pipx\venvs\bilibili-cli\Lib\site-packages\bili_cli\auth.py` 得到确切机制：

```python
CREDENTIAL_TTL_DAYS = 7          # 第36行：本地文件超7天 → 触发浏览器刷新
```

失效链路（`get_credential(mode="read")`）：
1. 读 `credential.json` → 若 `time.time() - saved_at > 7天` → 尝试 `_extract_browser_credential()`
2. 浏览器抽取失败 → 回退验证原凭证 `_validate_credential()`
3. 验证抛 `ResponseCodeException` → `validation is False` → **`clear_credential()` 直接 unlink，无备份、无提示**
4. 只有抛 `NetworkException` 才返回 `None`（保留文件）

**关键结论**：B站随时可能吊销手动复制的 SESSDATA（多设备风控等），而 CLI **一旦确认无效就立即删文件**。
所以体感是"很快过期"，实际是"被吊销 + 立即删除"两件事叠加。

### 本机浏览器自动恢复能力 = 零（必读）

CLI 的 recovery 路径靠 `browser-cookie3`，实测本机四种浏览器全部失败：

| 浏览器 | 实测结果 |
|---|---|
| Chrome | `BrowserCookieError: Failed to find cookies`（**未安装**，无 Cookie DB） |
| Firefox | `Could not find Firefox profile directory` |
| **Edge** | `RequiresAdminError: This operation requires admin`（唯一在用的浏览器） |
| Brave | 无 Cookie DB |

Edge 同时满足：① 运行中 Cookie DB 被锁 ② 新版用 App-Bound Encryption，`browser_cookie3` 无权解密。
→ **`bili login` 扫码与自动刷新都指望不上，唯一可行路径是手工粘 cookie。**

### 因此：SESSDATA 必须留副本 ⭐

CLI 会静默删文件，**务必把 SESSDATA/bili_jct/dedeuserid 另存一份**（归档或密码管理器），
否则每次失效都得重新登录 Edge + F12 抓，纯浪费。

### 手工重配流程（唯一可用路径）

1. Edge 登录 bilibili.com → F12 → Application → Cookies → `https://www.bilibili.com`
2. 复制三个值：`SESSDATA`、`bili_jct`、`dedeuserid`
3. 写入 `~/.bilibili-cli/credential.json`，**UTF-8 无 BOM**：

```python
import json, os, time
data = {"sessdata": "...", "bili_jct": "...", "ac_time_value": "",
        "buvid3": "", "buvid4": "", "dedeuserid": "...",
        "saved_at": time.time()}      # saved_at 必须有，否则被判 stale
p = r"~/.bilibili-cli/credential.json"
os.makedirs(os.path.dirname(p), exist_ok=True)
open(p, "w", encoding="utf-8", newline="\n").write(json.dumps(data, indent=2, ensure_ascii=False))
```

4. **无损验证**（不要用 `bili status`，见下）

```powershell
$ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
$sess = "<SESSDATA 值>"     # ⚠️ 必须先赋值给变量，值里含 % 和 *，直接内联会被 PS 解析吃掉
curl.exe -s -H "User-Agent: $ua" -H "Referer: https://www.bilibili.com/" `
  -H "Cookie: SESSDATA=$sess" "https://api.bilibili.com/x/web-interface/nav"
# ✅ 有效：code=0, data.isLogin=true, data.uname=<用户名>, data.mid=<uid>
# ❌ 无效：code=-101（未登录）
# 该接口是只读的，验证失败也不会动 credential.json
```

### 🚨 绝不要用 `bili status` 做连通性测试

`bili status` 走 `common.get_credential(mode="read")` → `_validate_credential()`。
凭证一旦被判定无效 → **当场 `clear_credential()` 删除文件**（见上方失效链路第 3 步）。
即「我只想看看还活着没」这个动作本身会把凭证弄丢。**永远先用 `nav` 接口无损确认。**

### 姐妹 CLI 对比：只有 bili 会自毁 ⭐

同一作者（jackwener/public-clis）的生态里，TTL/刷新逻辑同源，但**失效后的处理策略不同**：

| CLI | TTL 常量 | TTL 触发后刷新失败 | 验证失败是否删文件 |
|---|---|---|---|
| **bilibili-cli** | `CREDENTIAL_TTL_DAYS = 7`（auth.py:37） | 回退验证 → 无效则 **`clear_credential()` 删档** | ⚠️ **会，静默删除** |
| rdt-cli | `CREDENTIAL_TTL_DAYS = 7`（auth.py:23） | `logger.warning("Cookie refresh failed; using existing cookies")` → **保留** | ✅ 不会，保留文件 |
| xiaohongshu-cli | — | — | 未检出同类逻辑 |

source：`pipx\venvs\<pkg>\Lib\site-packages\<pkg>_cli\auth.py`

**结论**：bili 是这套生态里的异常分子。别把「CLI 会删我凭证」当成普遍规律，
但**对 bili 必须留副本**。

### 命令鉴权需求

| 命令 | 是否需登录 |
|---|---|
| `hot` / `search` / `video` / `rank` / `user` / 字幕 | ❌ 免登录 |
| `favorites` / `watch-later` / `history` / `feed` / `like` / `coin` / `triple` | ✅ 需登录 |

## 注意

> **bilibili-cli 自身**（`bili` 命令）走官方 API 且请求头正确，实测不触发 412。
> 但 **yt-dlp 直连已 412**（2026-09-10 实测），`space/arc/search` 类接口也 412 或 -799，
> 需要这类数据时改走 `x/web-interface/view` 逐条取。
> 如果 `bili` 遇到 `HTTP 412` / `RateLimitError`，稍等重试或减小 `--max`。
> 建议用 `--yaml` 输出，对 AI agent 更友好（非 TTY 环境默认输出 YAML）。

### 输出格式速查（选错会白跑）

| 命令 | 有 `--yaml`/`--json`？ | 备注 |
|---|---|---|
| `video` / `rank` / `hot` / `user` / `user-videos` | ✅ | `user-videos` 的 owner/stats 可能为空，需再查 view |
| `search --type video` | ✅ | 返回扁平数组（bvid/title/author/play/duration），**无 pubdate** |
| `search`（默认搜用户） | ✅ | `--type user` 时结构不同 |
| `audio` | ❌ | 无结构化输出，且已失效（见坑位清单） |
| `status` / `login` / `whoami` | ❌ | 纯文本 |
