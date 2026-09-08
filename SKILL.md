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
  分类：search / social (小红书/推特/B站/V2EX/Reddit) / career(LinkedIn) / dev(github) / web(网页/文章/RSS) / video(YouTube/B站/播客)。
triggers:
  - search: 搜/查/找/search/搜索/查一下/帮我搜
  - wechat: 微信/公众号/微信文章/搜微信/查公众号/wechat
  - social:
    - 小红书: xiaohongshu/xhs/小红书/红书
    - Twitter: twitter/推特/x.com/推文
    - B站: bilibili/b站/哔哩哔哩
    - V2EX: v2ex
    - Reddit: reddit
    - 豆瓣: douban/豆瓣/影评/豆瓣评分/豆瓣短评/电影评分
  - career: 招聘/职位/求职/linkedin/领英/找工作
  - dev: github/代码/仓库/gh/issue/pr/分支/commit
  - web: 网页/链接/文章/rss/读一下/打开这个
  - video: youtube/视频/播客/字幕/小宇宙/转录/yt/文字稿/转文字/音频转写
  - transcribe: 转录/转文字/文字稿/字幕/语音转文字/音频转文字/视频转文字
  - finance: 雪球/股票/stock/xueqiu/行情/基金
metadata:
  source: Agent-Reach (adapted for Hermes Agent)
  homepage: https://github.com/Panniantong/Agent-Reach
---

# Agent Reach — 路由器

14 平台工具集合。根据用户意图选择对应分类。

## 路由表（第一层直达）

| 用户意图 | 平台/分类 | 详细文档 |
|---------|------|---------|
| 知乎搜索/热榜/直答 | zhihu | [references/zhihu.md](references/zhihu.md)（官方 CLI） |
| 雪球帖子/讨论/大V观点 | xueqiu | [references/xueqiu.md](references/xueqiu.md)（snowball-cli） |
| 小红书 | xhs | [references/xiaohongshu.md](references/xiaohongshu.md) |
| Twitter/X | twitter | [references/twitter.md](references/twitter.md) |
| B站 | bili | [references/bilibili.md](references/bilibili.md) |
| V2EX | v2ex | [references/v2ex.md](references/v2ex.md)（公开API） |
| Reddit | reddit | [references/reddit.md](references/reddit.md) |
| 微信公众号文章搜索 | wechat | [references/wechat.md](references/wechat.md) |
| 网页搜索/代码搜索 | search | [references/search.md](references/search.md) |
| 豆瓣（电影/影评/短评） | douban | [references/douban.md](references/douban.md) |
| 招聘/职位/LinkedIn | career | [references/career.md](references/career.md) |
| GitHub/代码 | dev | [references/dev.md](references/dev.md) |
| 网页/文章/RSS | web | [references/web.md](references/web.md) |
| YouTube/播客字幕 | video | [references/video.md](references/video.md) |

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

- [搜索工具](references/search.md) — Exa AI 搜索
- [知乎](references/zhihu.md) — 官方 Zhihu CLI：搜索/热榜/直答/额度
- [雪球](references/xueqiu.md) — snowball-cli：帖子/讨论/KOL观点（行情兜底走东财API）
- [小红书](references/xiaohongshu.md) — xhs-cli
- [Twitter/X](references/twitter.md) — twitter-cli
- [B站](references/bilibili.md) — bilibili-cli
- [V2EX](references/v2ex.md) — 公开 API
- [Reddit](references/reddit.md) — rdt-cli
- [豆瓣抓取](references/douban.md) — 电影/影评/短评，rexxar 移动版 API（免登录免验证码）
- [职场招聘](references/career.md) — LinkedIn
- [开发工具](references/dev.md) — GitHub CLI
- [网页阅读](references/web.md) — Jina Reader, RSS, 各工具选型对比
- [网页工具速查](references/web-tools.md) — 搜索 vs 读取，一页速查
- [视频播客](references/video.md) — YouTube, B站, 小宇宙
- [转录格式规范](scripts/transcribe_format.md) — 转录文字稿格式化规则
- [X/Twitter 获取路径对比](references/x-comparison.md) — twitter-cli (免费) vs x_search (付费稳定+AI总结)

## 配置渠道

如果某个 channel 需要配置，获取安装指南：
https://raw.githubusercontent.com/Panniantong/agent-reach/main/docs/install.md

用户只需提供 cookies，其他配置由 agent 完成。

---

## Twitter/X 认证配置

### 凭据位置

Hermes `.env` 中已配置 `TWITTER_AUTH_TOKEN` 和 `TWITTER_CT0` 环境变量，twitter-cli 会自动读取。

### 路径选择

Twitter/X 内容获取有**三条路**：twitter-cli（免费）、x_search（付费稳定+AI总结）、bird-cli（趋势功能）。
详见 [X/Twitter 获取路径对比](references/x-comparison.md)。

### 验证凭据是否有效

```bash
twitter user @username --yaml 2>&1
```

如果返回 `ok: true` + 用户资料数据，说明凭据有效。如果返回 `401 Unauthorized`，需要更新 cookie。

### 支持的 twitter-cli 命令

```bash
twitter feed -n 20                  # 首页时间线
twitter tweet URL_OR_ID             # 单条推文 + 回复
twitter article URL_OR_ID           # 长文 / X Article
twitter user-posts @username -n 20  # 用户时间线
twitter user @username              # 用户资料
twitter search "query" -n 10        # 搜索（可能不稳定）
```

### 更新凭据

Cookie 过期时需要重新导出。获取方式：
1. 浏览器装 Cookie-Editor 插件
2. 登录 x.com → 插件 Export → Header String
3. 把 `auth_token=` 和 `ct0=` 的值更新到 Hermes `.env` 的 `TWITTER_AUTH_TOKEN` / `TWITTER_CT0`