# 视频转录（B站 / YouTube / 小红书 / 小宇宙播客）

覆盖四个视频/播客平台的字幕和转录：**YouTube、B站（Bilibili）、小红书视频笔记、小宇宙播客**。通用 URL 也可用 transcribe.py 自动识别。

## YouTube (yt-dlp)

> ### ⚠️ 本机当前状态：不可用（2026-09-18 实测）
>
> ### ✅ 本机当前状态：可用（2026-10-02 实测恢复）
>
> `yt-dlp -F "https://www.youtube.com/watch?v=..."` RC=0，全部格式可列出（含 4K），
> 无 "Sign in to confirm you're not a bot" / LOGIN_REQUIRED 报错。走 visionos player API + node 解 JS challenge。
> 可能原因：代理出口节点更换、yt-dlp 2026.08.19 的 visionos client 生效、或 YouTube 侧策略变化。
>
> **历史记录（2026-09-18 曾全灭，供回退参考）**：当时出口 `64.110.82.17` 属 Oracle Cloud 首尔机房
> （ASN 31898），数据中心 IP 被 YouTube 判定为机器人，强制要求登录。已实测排除：换 `player_client`
> （tv / web_safari / mweb / ios / android / web_embedded / tv_simply，7/7 全败）、网络不通（web 页面
> HTTP 200、oEmbed 正常）。**若再次出现 LOGIN_REQUIRED，可参考当时的解法**：换非数据中心出口节点，
> 或配置 PO Token provider（`bgutil-ytdlp-pot-provider`，官方推荐，配 `mweb` client）。
> 见 [PO Token Guide](https://github.com/yt-dlp/yt-dlp/wiki/PO-Token-Guide)。
>
> ⚠️ 本次仅验证了格式侦察（-F），**真实下载尚未实测**，首次下载长视频前建议先 `-F` 确认。

### 获取视频元数据

```bash
yt-dlp --dump-json "URL"
```

### 下载字幕

```bash
# 下载字幕 (不下载视频)
yt-dlp --write-sub --write-auto-sub --sub-lang "zh-Hans,zh,en" --skip-download -o "/tmp/%(id)s" "URL"

# 然后读取 .vtt 文件
Get-Content /tmp/VIDEO_ID.*.vtt
```

### 获取评论

```bash
# 提取评论（best-effort，不保证完整）
yt-dlp --write-comments --skip-download --write-info-json `
  --extractor-args "youtube:max_comments=20" `
  -o "/tmp/%(id)s" "URL"
# 评论在 .info.json 的 comments 字段中
```

### 搜索视频

```bash
yt-dlp --dump-json "ytsearch5:query"
```

### 无字幕兜底：Whisper 音频转写

使用 `transcribe.py` 统一转录脚本：

```bash
python <skill-path>/scripts/transcribe.py "URL" [输出目录]
```

## B站 / Bilibili

`bili`（bilibili-cli）用于**元数据/字幕/评论**；**下载视频文件用 yt-dlp**。

### ⭐ 下载视频 / 音频（2026-09-18 实测通过）

```bash
# 视频（自动选最佳画质+音轨并合并为 mp4）
yt-dlp -f "bv*+ba/b" --merge-output-format mp4 "https://www.bilibili.com/video/BVxxx"

# 只下音频
yt-dlp -f "ba/b" -x --audio-format m4a "URL"

# 只看能下什么、不下（先侦察）
yt-dlp -F "URL"

# 字幕（不下视频）
yt-dlp --write-sub --write-auto-sub --sub-lang "zh-Hans,zh,en" --convert-subs srt --skip-download "URL"
```

**实测数据**（BV1uv411q7Mv，未登录态）：1920x1080 hevc + aac，77.60 MB，时长校验 313.3865s ✅。
**未登录也能拿到 1080P**，不必先登录。

### ⚠️ 版本红线：yt-dlp 必须 ≥ 2026.07.04

| 版本 | B站 表现 |
|---|---|
| < 2026.07.04（如 2026.03.17） | ❌ 恒 `HTTP Error 412 Precondition Failed`，无法下载 |
| ≥ 2026.07.04（如 2026.08.19） | ✅ 正常，3/3 实测通过 |

**根因**（2026-09-18 定位）：旧版 yt-dlp 调用 `x/player/wbi/playurl` 时用 `bvid=` 传参，B站 对该参数形态恒定返回 412；
改用 `avid=` 则正常。官方已在 **2026.07.04** 发布 `bilibili: Fix API extraction`
（[issue #13730](https://github.com/yt-dlp/yt-dlp/issues/13730)，commit `e8de28e2`）修复。

> **排查陷阱**：这个 412 与代理、Cookie、UA、Referer、fnval、wbi 签名、限流**全都无关** —— 以上变量均已逐一实测排除
> （含对同接口连发 40 次全 200）。见到 412 先查版本，别去折腾代理和请求头。

```bash
# 升级（PyInstaller onedir 版自带自更新）
yt-dlp -U
yt-dlp --version   # 确认 ≥ 2026.07.04
```

### 🚫 不要用 `bili audio`

`bili audio` 子命令会取到流地址并开始下载，但**卡死无产物**（2026-09-18 在 v0.6.2 复测：
300s 超时强杀，只落 3881 字节半成品）。**下载一律走 yt-dlp。**

### 视频元数据

```bash
bili video BV19xwKeTEye
bili video BV19xwKeTEye --yaml          # 结构化输出
```

### 字幕

```bash
# 纯文本字幕
bili video BV19xwKeTEye --subtitle

# 带时间线字幕
bili video BV19xwKeTEye --subtitle-timeline

# 导出 SRT 格式
bili video BV19xwKeTEye -st --subtitle-format srt
```

### AI 总结

```bash
bili video BV19xwKeTEye --ai            # B站 AI 总结
```

### 转录流水线

```bash
python <skill-path>/scripts/transcribe.py "https://www.bilibili.com/video/BVxxx" [输出目录]
```

## 小红书 / XiaoHongShu (xhs CLI + 内嵌字幕)

小红书视频笔记通常带人声讲解，很多有内嵌中文字幕。直接从 `xhs read` 返回的 JSON 中提取 SRT 字幕URL并下载，无需音频转写。

### 字幕提取流程（三级兜底）

| 优先级 | 方式 | 条件 | 说明 |
|:------:|:----|:-----|:-----|
| 1 | **内嵌字幕 SRT** | `subtitles.zh-CN` 存在 | 最快最省，直接下载字幕文件 |
| 2 | **视频音频 + Whisper** | 视频流含 `audio_codec: aac` | 无字幕时自动取流 → yt-dlp下载 → Groq Whisper转录 |
| 3 | **desc 文字** | 纯图片笔记或无上述条件 | 直接使用描述文字 |

### 转录流水线（统一入口）

```bash
# 通过 URL
python <skill-path>/scripts/transcribe.py "https://www.xiaohongshu.com/explore/699da865000000000e03ca2b"

# 通过裸 note_id（24位hex）
python <skill-path>/scripts/transcribe.py "699da865000000000e03ca2b"
```

自动识别 `xiaohongshu.com/explore/` 或 24位hex字符串，走字幕提取而非Whisper转录。

## 小宇宙播客 / Xiaoyuzhou Podcast

### 转录单集播客

```bash
# 转录
python <skill-path>/scripts/transcribe.py "https://www.xiaoyuzhoufm.com/episode/EPISODE_ID"
```

### 前置要求

1. **ffmpeg**: 需在 PATH 中（本机在 `C:\Green Software\yt-dlp\ffmpeg.exe`）
2. **Groq API Key**: 已配置在 Hermes `.env` 的 `GROQ_API_KEY`
3. **yt-dlp**: 需已安装，且 **≥ 2026.07.04**（见 B站 章节的版本红线）

## 选择指南

| 场景 | 推荐工具 |
|-----|---------|
| **B站 下载视频/音频** | **yt-dlp**（必须 ≥ 2026.07.04） |
| YouTube 下载 / 字幕 | yt-dlp — ✅ **2026-10-02 实测恢复可用**（格式侦察 RC=0 含 4K；真实下载建议先 `-F` 确认，历史拦截记录见上方） |
| B站视频元数据/字幕/评论 | bilibili-cli |
| 小红书字幕 | transcribe.py（xhs read + 内嵌SRT） |
| 播客转录 | transcribe.py |
| 无字幕音视频 | transcribe.py（Groq Whisper 兜底） |

## 本机工具路径与版本（2026-09-18）

| 工具 | 路径 | 说明 |
|---|---|---|
| yt-dlp | `C:\Green Software\yt-dlp\yt-dlp.exe` | PyInstaller onedir，`yt-dlp -U` 自更新 |
| ffmpeg / ffprobe | `C:\Green Software\yt-dlp\` | 外置独立文件，**升级 yt-dlp 不会动它们** |
| bili (bilibili-cli) | `bili` | v0.6.2，凭证见 bilibili.md |

> **升级 yt-dlp 的坑**：`C:\Green Software\yt-dlp\` 里同时放着 ffmpeg 三件套（共约 280MB）。
> 用 `yt-dlp -U` 升级是安全的（只替换 yt-dlp 本体 + `_internal/`），
> **不要**手动整目录覆盖。升级前建议先备份 `yt-dlp.exe` + `_internal/`（约 21MB）。