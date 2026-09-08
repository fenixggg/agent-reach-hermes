# 多平台视频转录与字幕 (Video & Audio Transcription)

> **支持平台矩阵**：
> 1. **YouTube**：免登录原生/自动多语言字幕下载 (`yt-dlp`)、视频信息解析、无字幕音轨提取转写
> 2. **B站 (Bilibili)**：`bilibili-cli` 原生直连提取官方字幕/AI总结，或兜底下载音频转写
> 3. **小红书 (XiaoHongShu)**：短视频与图文笔记内嵌 SRT 字幕自动提取、音轨拉取转录
> 4. **小宇宙播客 (Xiaoyuzhou)**：单集播客音频抓取与超长语音切片转文字稿
> 5. **通用音视频**：本地文件或任意支持格式音频，通过云端 Groq Whisper Large-v3 秒级转文字

## 安装与环境依赖

```bash
# 1. 媒体下载器 yt-dlp (各平台视频拉取核心)
# Windows 推荐 winget 或 pip:
pip install yt-dlp

# 2. 系统核心依赖 ffmpeg (音视频格式转换与切片必备)
# 必须配置在系统 PATH 环境变量中

# 3. 云端 Whisper API (高速转文字)
# 在 profile .env 中配置 GROQ_API_KEY=gsk_xxxx (免费层已足够高频使用)
```

## 1. 统一转录入口脚本 (transcribe.py)

无需关心底层各平台的取流差异，直接传 URL 或 ID 即可：

```bash
# 语法: python scripts/transcribe.py "<URL或ID>" [可选指定输出目录]

# YouTube 视频
python scripts/transcribe.py "https://www.youtube.com/watch?v=VIDEO_ID"

# B站视频 (支持 URL 或 BV 号)
python scripts/transcribe.py "https://www.bilibili.com/video/BV19xwKeTEye"
python scripts/transcribe.py "BV19xwKeTEye"

# 小红书视频笔记 (支持 URL 或 24位 hex note_id)
python scripts/transcribe.py "https://www.xiaohongshu.com/explore/699da865000000000e03ca2b"

# 小宇宙播客
python scripts/transcribe.py "https://www.xiaoyuzhoufm.com/episode/EPISODE_ID"
```

---

## 2. YouTube (yt-dlp 详细命令)

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

使用 `bili` 命令（bilibili-cli），优先于 yt-dlp。

### 视频元数据

```bash
# 视频详情（含统计、时长、UP主等）
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

### 备选：yt-dlp（当 bili-cli 不可用时）

```bash
# 元数据
yt-dlp --dump-json "https://www.bilibili.com/video/BVxxx"

# 字幕
yt-dlp --write-sub --write-auto-sub --sub-lang "zh-Hans,zh,en" --convert-subs vtt --skip-download -o "/tmp/%(id)s" "URL"
```

> **注意**: yt-dlp 直连 B站 API 可能遇到 412 反爬拦截（当前环境已验证）。优先使用 bilibili-cli。

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

1. **ffmpeg**: 需在 PATH 中
2. **Groq API Key**: 已配置在 Hermes `.env` 的 `GROQ_API_KEY`
3. **yt-dlp**: 需已安装

## 选择指南

| 场景 | 推荐工具 |
|-----|---------|
| YouTube 字幕 | yt-dlp |
| B站视频元数据/字幕 | bilibili-cli（首选） / yt-dlp（备选） |
| 小红书字幕 | transcribe.py（xhs read + 内嵌SRT） |
| 播客转录 | transcribe.py |
| 无字幕音视频 | transcribe.py（Groq Whisper 兜底） |