---
name: agent-reach
description: >
  MUST USE when user asks to search, browse, read, or interact with content from any of these platforms:
  微信公众号/微信/wechat, 小红书/xiaohongshu/xhs, Twitter/推特/X, B站/bilibili,
  V2EX, Reddit, LinkedIn/领英, YouTube, GitHub code search,
  小宇宙播客, 雪球/股票行情, RSS feeds, 豆瓣/douban（电影/影评/短评）, or any web URL.

  Also MUST USE for: web搜索/搜/查/找/look up/research, 招聘/求职/jobs, 分享的链接/URL.
  Routes to CLI tools: wechat_search.py, xhs-cli, twitter-cli, bili, rdt-cli, gh, yt-dlp, curl+Jina.
  14 platforms. Zero config for 7 channels.

  【路由方式】SKILL.md 包含路由表和常用命令，复杂场景需按需阅读对应分类的 references/*.md。
  分类：social (微信/小红书/知乎/B站/雪球/豆瓣/V2EX/推特/Reddit/LinkedIn/GitHub) / video (视频转录与字幕: YouTube/B站/小红书/小宇宙播客) / web (网页/文章/RSS)。
triggers:
  - social:
    - 微信: 微信/公众号/微信文章/搜微信/查公众号/wechat
    - 小红书: xiaohongshu/xhs/小红书/红书
    - 知乎: 知乎/zhihu/知乎搜索/知乎热榜/知乎直答
    - B站: bilibili/b站/哔哩哔哩
    - 雪球: 雪球/股票/stock/xueqiu/行情/基金/大V
    - 豆瓣: douban/豆瓣/影评/豆瓣评分/豆瓣短评/电影评分
    - V2EX: v2ex
    - Twitter: twitter/推特/x.com/推文
    - Reddit: reddit
    - LinkedIn: linkedin/领英/招聘/职位/求职/找工作
    - GitHub: github/代码/仓库/gh/issue/pr/分支/commit
  - video:
    - 视频转录: 视频/视频转录/字幕/音频转写/转文字/文字稿/音视频提取
    - 支持平台: YouTube/油管/yt/B站视频/bilibili字幕/小红书视频/小宇宙/播客
  - web: 网页/链接/文章/rss/读一下/打开这个/web阅读
metadata:
  source: Agent-Reach (adapted for Hermes Agent)
  homepage: https://github.com/Panniantong/Agent-Reach
---

# Agent Reach — 路由器

14 平台工具集合。根据用户意图选择对应分类。

## 路由表（第一层直达）

### 1. 国内社交与主流平台（按常用热度排序）

| 平台 / 意图 | 标识 | 核心功能 | 详细文档 |
|:---|:---:|:---|:---|
| **微信公众号** | wechat | 搜狗微信直搜、落地真实 URL 解析、极速提取 | [references/wechat.md](references/wechat.md) |
| **小红书** | xhs | 笔记搜索、图文正文、评论读取（带 xsec） | [references/xiaohongshu.md](references/xiaohongshu.md) |
| **知乎** | zhihu | 官方 CLI：知乎搜索、全网搜索、热榜、直答 | [references/zhihu.md](references/zhihu.md)（官方 CLI） |
| **B站 (哔哩哔哩)** | bili | 视频详情、免登录字幕提取、热门排行榜、动态 | [references/bilibili.md](references/bilibili.md) |
| **雪球** | xueqiu | 投资热帖、个股 KOL 讨论流、社区观点（行情兜底） | [references/xueqiu.md](references/xueqiu.md)（snowball-cli） |
| **豆瓣** | douban | 电影/影视详情、长篇影评、短评深度抓取（Rexxar API） | [references/douban.md](references/douban.md) |
| **V2EX** | v2ex | 程序员社区节点主题、全站热门（免登录官方API） | [references/v2ex.md](references/v2ex.md) |

### 2. 海外社交与开发者平台（按常用热度排序）

| 平台 / 意图 | 标识 | 核心功能 | 详细文档 |
|:---|:---:|:---|:---|
| **Twitter / X** | twitter | 时间线、推文详情、长文、用户资料 | [references/twitter.md](references/twitter.md) |
| **Reddit** | reddit | 社区帖子阅读、多层评论流、Subreddit 热门 | [references/reddit.md](references/reddit.md) |
| **LinkedIn (领英)** | career | 职场社交、公开档案与职位检索 | [references/career.md](references/career.md) |
| **GitHub** | github | 仓库检索、代码搜索、Issue / PR 处理 | [references/dev.md](references/dev.md) |

### 3. 多平台视频转录与网页阅读

| 类别 / 意图 | 标识 | 核心功能与支持网站 | 详细文档 |
|:---|:---:|:---|:---|
| **多平台视频转录与字幕** | video | **支持平台**：**YouTube**、**B站 (Bilibili)**、**小红书视频**、**小宇宙播客**<br>原生字幕提取 (yt-dlp/bili)、音频流拉取与 Groq Whisper Large-v3 极速转文字稿 | [references/video.md](references/video.md) |
| **网页阅读 / 正文提取** | web | Firecrawl 浏览器渲染、Jina Reader 降噪、RSS 聚合阅读 | [references/web.md](references/web.md) |

> 旧 `social.md` 已拆分为上述各平台独立文档，按行直达，不再需要先读 social 总览。

## 搜索路由优先级（用户偏好）

当用户要求"查/搜/找"时，按以下优先级选择工具：

| 优先级 | 场景 | 工具 | 说明 |
|:------:|------|------|------|
| 1 🥇 | **信息查询**（无具体URL） | **Tavily** | 结构化结果，AI友好。不要用 curl Jina 做搜索 |
| 2 🥈 | **读指定文章**（有URL） | **Firecrawl scrape** | 替代 Jina Reader，JS渲染更好、更可靠 |
| 3 🥉 | **读复杂页面**（JS渲染/需登录/需交互） | **Firecrawl interact** 或 Hermes Browser | 完整浏览器渲染 |
| 4 🚨 | **页面变化监控** | **Firecrawl monitor** | 定时检查，webhook通知 |

**原则：** Tavily 搜信息 → Firecrawl 读文章 → Firecrawl interact 处理交互页面。不要反着来。

Firecrawl 已安装，API Key 已配置，31 个相关 skills 已就绪。

## 零配置快速命令

```bash
# 微信公众号搜索与直链解析 (解密真实 mp.weixin.qq.com 链接)
python <skill-path>/scripts/wechat_search.py "关键词" --limit 5

# 微信文章全文深度抓取 (推荐配合 better-webfetch 或通用抓取工具)
python <skills-path>/better-webfetch/scripts/fetch.py "微信直链URL"

# 通用网页阅读 (Firecrawl — 首选)
firecrawl scrape "URL" -o .firecrawl/page.md

# 通用网页阅读 (Jina Reader — 备选)
curl -s "https://r.jina.ai/URL"

# GitHub 搜索
gh search repos "query" --sort stars --limit 10

# Twitter 搜索
twitter search "query" -n 10

# B站视频详情
bili video BVxxx --yaml

# B站字幕
bili video BVxxx --subtitle

# YouTube/B站字幕 (yt-dlp 备选)
yt-dlp --write-sub --skip-download -o "/tmp/%(id)s" "URL"

# Reddit 搜索
rdt search "query" --limit 10

# Reddit 读帖 + 评论
rdt read POST_ID

# V2EX 热门
curl -s "https://www.v2ex.com/api/topics/hot.json" -H "User-Agent: agent-reach/1.0"

# 小红书搜索
xhs search "query"

# 小红书读笔记
xhs read NOTE_ID_OR_URL

# 视频转录（B站/YouTube/小红书/通用）
python <skill-path>/scripts/transcribe.py "URL" [输出目录]
```

## 环境检查

```bash
# 检查可用 CLI 工具
where xhs twitter bili rdt gh yt-dlp python 2>nul
pip list 2>nul | findstr "xiaohongshu-cli twitter-cli bilibili-cli rdt-cli"
```

## 工作区规则

不要在 agent workspace 创建文件。使用 `%TEMP%` 存放临时输出，`~/.agent-reach/` 存放持久数据。

## 详细文档

根据用户需求，阅读对应的详细文档：

- [知乎](references/zhihu.md) — 官方 Zhihu CLI：搜索/热榜/直答/额度
- [雪球](references/xueqiu.md) — snowball-cli：帖子/讨论/KOL观点（行情兜底走东财API）
- [小红书](references/xiaohongshu.md) — xhs-cli
- [Twitter/X](references/twitter.md) — twitter-cli
- [B站](references/bilibili.md) — bilibili-cli
- [V2EX](references/v2ex.md) — 公开 API
- [Reddit](references/reddit.md) — rdt-cli
- [豆瓣抓取](references/douban.md) — 电影/影评/短评，rexxar 移动版 API（免登录免验证码）
- [职场招聘](references/career.md) — LinkedIn
- [GitHub / 代码工具](references/dev.md) — GitHub CLI (gh)
- [网页阅读](references/web.md) — Jina Reader, RSS, 各工具选型对比
- [网页工具速查](references/web-tools.md) — 搜索 vs 读取，一页速查
- [多平台视频转录与字幕](references/video.md) — YouTube, B站, 小红书视频, 小宇宙播客
- [转录格式规范](scripts/transcribe_format.md) — 转录文字稿格式化规则
- [X/Twitter 获取路径对比](references/x-comparison.md) — twitter-cli (免费) vs x_search (付费稳定+AI总结)