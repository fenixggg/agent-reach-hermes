---
name: agent-reach
description: >
  MUST USE when user asks to search, browse, read, or interact with content from any of these platforms:
  微信公众号/微信/wechat, 小红书/xiaohongshu/xhs, Twitter/推特/X, B站/bilibili/哔哩哔哩,
  V2EX, Reddit, LinkedIn/领英, YouTube, GitHub code search,
  小宇宙播客, 雪球/股票行情, 微博/weibo/热搜, RSS feeds, 豆瓣/douban（电影/影评/短评）,
  今日头条/toutiao/头条/微头条, or any web URL.

  Also MUST USE for: web搜索/搜/查/找/look up/research, 招聘/求职/jobs, 分享的链接/URL.
  Routes to CLI tools: wechat_search.py, zhihu-cli, snowball-cli, xhs-cli, twitter-cli, bili, rdt-cli, gh, yt-dlp, curl+Jina, s_toutiao.py.
  15 platforms. Zero config for 8 channels.

  【路由方式】SKILL.md 包含路由表和常用命令，复杂场景需按需阅读对应分类的 references/*.md。
  分类：search / 国内平台(微信/知乎/雪球/微博/B站/小红书/豆瓣/V2EX/头条) / 国外平台(Twitter/Reddit/YouTube) / github / career(LinkedIn) / web(网页/文章/RSS)。
triggers:
  - search: 搜/查/找/search/搜索/查一下/帮我搜
  - wechat: 微信/公众号/微信文章/搜微信/查公众号/wechat
  - social:
    - 小红书: xiaohongshu/xhs/小红书/红书
    - Twitter: twitter/推特/x.com/推文
    - B站: bilibili/b站/哔哩哔哩
    - 微博: weibo/微博/热搜
    - V2EX: v2ex
    - Reddit: reddit
    - 豆瓣: douban/豆瓣/影评/豆瓣评分/豆瓣短评/电影评分
    - 今日头条: toutiao/头条/今日头条/微头条
  - career: 招聘/职位/求职/linkedin/领英/找工作
  - github: github/代码/仓库/gh/issue/pr/分支/commit
  - web: 网页/链接/文章/rss/读一下/打开这个
  - video: youtube/视频/播客/字幕/小宇宙/转录/yt/文字稿/转文字/音频转写
  - transcribe: 转录/转文字/文字稿/字幕/语音转文字/音频转文字/视频转文字
  - finance: 雪球/股票/stock/xueqiu/行情/基金/雪球帖子/大V观点
---

# Agent Reach — 路由器

15 平台工具集合。根据用户意图选择对应分类。

## 路由表（第一层直达，社交平台按国内/国外分列，按使用频率排序）

### 国内平台

| 用户意图 | 平台 | 详细文档 |
|---------|------|---------|
| 微信公众号文章搜索 | wechat | [references/wechat.md](references/wechat.md) |
| 知乎 搜索/热榜/直答 | zhihu | [references/zhihu.md](references/zhihu.md)（官方 CLI） |
| 雪球 帖子/讨论/大V观点 | xueqiu | [references/xueqiu.md](references/xueqiu.md)（snowball-cli） |
| 微博 热搜/搜索/评论/大V | weibo | [references/weibo.md](references/weibo.md)（weibo-cli + 搜索脚本） |
| Bilibili/哔哩哔哩/B站 | bili | [references/bilibili.md](references/bilibili.md) |
| 小红书 | xhs | [references/xiaohongshu.md](references/xiaohongshu.md) |
| 豆瓣（电影/影评/短评） | douban | [references/douban.md](references/douban.md) |
| V2EX | v2ex | [references/v2ex.md](references/v2ex.md)（公开API） |
| 今日头条 文字内容（搜索/正文/评论/热榜） | toutiao | [references/toutiao.md](references/toutiao.md)（s_toutiao.py，免登录；**视频不支持**） |

### 国外平台

| 用户意图 | 平台 | 详细文档 |
|---------|------|---------|
| Twitter/X | twitter | [references/twitter.md](references/twitter.md) |
| Reddit | reddit | [references/reddit.md](references/reddit.md) |
| YouTube/播客字幕 | video | [references/video.md](references/video.md) |

### 通用工具（不分国内外）

| 用户意图 | 分类 | 详细文档 |
|---------|------|---------|
| 网页搜索/代码搜索 | search | [references/search.md](references/search.md) |
| 网页/文章/RSS | web | [references/web.md](references/web.md) |
| GitHub/代码 | github | [references/github.md](references/github.md) |
| 招聘/职位/LinkedIn | career | [references/career.md](references/career.md) |

> 旧 `social.md` 已拆分为上述各平台独立文档，按行直达，不再需要先读 social 总览。

## 搜索路由优先级（用户偏好）

当用户要求"查/搜/找"时，按以下优先级选择工具：

| 优先级 | 场景 | 工具 | 说明 |
|:------:|------|------|------|
| 1 🥇 | **信息查询**（无具体URL） | **Tavily** | 结构化结果，AI友好。不要用 curl Jina 做搜索 |
| 2 🥈 | **读指定文章**（有URL） | **Firecrawl scrape** | 替代 Jina Reader，JS渲染更好、更可靠 |
| 3 🥉 | **读复杂页面**（JS渲染/需登录/需交互） | **Firecrawl interact** 或宿主 Agent 的浏览器工具 | 完整浏览器渲染 |
| 4 🚨 | **页面变化监控** | **Firecrawl monitor** | 定时检查，webhook通知 |

**原则：** Tavily 搜信息 → Firecrawl 读文章 → Firecrawl interact 处理交互页面。不要反着来。

Firecrawl 已安装，API Key 已配置，31 个相关 skills 已就绪。

## 零配置快速命令

```bash
# 微信公众号搜索与直链解析 (解密真实 mp.weixin.qq.com 链接)
python <skill-path>/scripts/wechat_search.py "关键词" --limit 5

# 微信文章全文深度抓取 (首选 better-webfetch，零成本且清洗最干净)
python "<skills-path>/better-webfetch/scripts/fetch.py" "微信直链URL"

# 通用网页阅读 (Firecrawl — 首选；⚠️ 勿裸调 PATH 里的 firecrawl——它读到 HTTP_PROXY 环境变量
#   bash <skills-path>/firecrawl-cli/scripts/firecrawl.sh scrape "URL"
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

# 今日头条文字内容（免登录、免凭证、无硬性频率限制）
# ⚠️ 仅文字内容：图文/微头条/评论/热榜。视频抓取技术不可行，已放弃。
python <skill-path>/scripts/s_toutiao.py search "关键词" --limit 10
python <skill-path>/scripts/s_toutiao.py search "关键词" --type weitoutiao   # 微头条
python <skill-path>/scripts/s_toutiao.py search "关键词" --type all          # 图文+微头条

# 今日头条读正文（自动判别 文章/微头条）+ 评论
python <skill-path>/scripts/s_toutiao.py read <gid或URL> --comments 20

# 今日头条热榜
python <skill-path>/scripts/s_toutiao.py hot --limit 50
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
- [雪球](references/xueqiu.md) — snowball-cli：股票基金数据查询 + 帖子讨论/KOL观点（行情兜底走东财API）
- [微博](references/weibo.md) — weibo-cli（热搜/详情/评论/用户）+ s_weibo_search.py（关键词搜索）
- [小红书](references/xiaohongshu.md) — xhs-cli
- [Twitter/X](references/twitter.md) — twitter-cli
- [B站](references/bilibili.md) — bilibili-cli
- [V2EX](references/v2ex.md) — 公开 API
- [Reddit](references/reddit.md) — rdt-cli
- [豆瓣抓取](references/douban.md) — 电影/影评/短评，rexxar 移动版 API（免登录免验证码）
- [今日头条](references/toutiao.md) — s_toutiao.py：**文字内容**专精——搜索/文章正文/微头条/评论/热榜，免登录免签名（移动版 SSR 解析）；⚠️ **视频不可抓**
- [职场招聘](references/career.md) — LinkedIn
- [GitHub](references/github.md) — GitHub CLI（gh）：仓库/代码/issue 搜索
- [网页阅读](references/web.md) — Jina Reader, RSS, 各工具选型对比
- [网页工具速查](references/web-tools.md) — 搜索 vs 读取，一页速查
- [视频转录](references/video.md) — YouTube / B站 / 小红书视频 / 小宇宙播客，字幕与转录
- [转录格式规范](scripts/transcribe_format.md) — 转录文字稿格式化规则
- [X/Twitter 获取路径对比](references/x-comparison.md) — twitter-cli (免费) vs x_search (付费稳定+AI总结)

## 配置渠道

各平台登录凭证（cookie/Access Secret）的存放位置、当前状态和恢复流程，统一记录在对应平台的 references/*.md 的「凭证存放位置」章节。新增平台或凭证失效时，先读对应 md。