# Agent-Reach for Hermes Agent

> **声明 / Attribution**:
> 本项目是基于 [Panniantong/Agent-Reach](https://github.com/Panniantong/Agent-Reach)（MIT License）针对 **Hermes Agent** 架构深度重构与适配的专有 Skill 版本。

---

## 🌟 简介

`agent-reach` 是专为 **Hermes Agent** 设计的全网信息触达与社交/内容平台采集 Skill。它将分散在各个平台的开源 CLI、官方开放接口及抓取脚本无缝聚合为清晰的路由器，赋予 AI 智能体直接读取全网公开内容、音视频字幕、社区讨论与行业动态的能力。

### ✨ 支持平台与能力矩阵

| 平台 / 类别 | 工具载体 | 核心能力 | 认证需求 |
| :--- | :--- | :--- | :--- |
| **知乎 (Zhihu)** | 官方 Zhihu CLI | 搜索、热榜、直答 | 需平台 Secret |
| **微博 (Weibo)** | `weibo-cli` + 内置搜索脚本 | 热搜榜、正文/评论、网页稳定搜索 | 免登录 / 需 Cookie |
| **今日头条 (Toutiao)** | `s_toutiao.py` | **文字内容专精**：搜索/正文/微头条/评论/热榜 (SSR解析) | 免登录 / 零凭证 |
| **雪球 (Xueqiu)** | `snowball-cli` | 实时热帖、KOL观点、社区讨论 | 需 Cookie |
| **小红书 (XHS)** | `xhs-cli` | 笔记搜索、图文阅读（带 xsec） | 需本地 Cookie |
| **推特 / X** | `twitter-cli` | 推文读取、用户主页、时间线 | 需 Auth Token |
| **B站 (Bilibili)** | `bilibili-cli` | 视频详情、官方原生字幕提取、用户动态 | 公开只读免登录 |
| **Reddit** | `rdt-cli` | 帖子阅读、评论流、Subreddit 热门 | 需 Session / JWT |
| **微信公众号** | `wechat_search.py` | 搜狗微信直搜、落地真实 URL 解析 | 免登录 |
| **V2EX** | 官方公开 API | 节点主题、全站热门 | 免登录 |
| **豆瓣电影** | Rexxar API | 电影详情、影评、短评深度抓取 | 免登录 |
| **多平台音视频转录** | `transcribe.py` (Whisper / yt-dlp) | 支持 YouTube、B站、小红书视频、小宇宙播客转文字稿 | 需 Groq API Key |
| **GitHub / 开发** | `gh` CLI | 代码库检索、Issue/PR 联动 | 需 GitHub Auth |
| **网页全文阅读** | Jina / Firecrawl / better-webfetch | 通用正文提取与降噪 | 视选型而定 |

## 💡 与原版（Panniantong/Agent-Reach）的区别与改进

原版 `Agent-Reach` 主要是作为一个独立的全局 Python CLI 工具包来设计和分发的。而在实际接入 **Hermes Agent** 的高频对话与自动化调度场景中，直接运行原始仓库会面临上下文开销大、缺少原生平台规范、反爬机制适配等痛点。本项目基于此做了以下核心改进：

1. **架构改造：从通用 CLI 转换为 Hermes 原生 Skill 规范**
   - 彻底解耦庞大的单一代码库，改造为标准 Hermes Skill 结构（`SKILL.md` + 模块化 `references/` + 辅助 `scripts/`）。
   - **两层路由体系（节省 Context）**：Agent 在触发时仅需加载第一层轻量级索引，只有需要深入特定平台交互时才按需读取单项平台的 Markdown 文档，极大降低 Token 消耗。

2. **新增关键平台与官方 CLI 适配**
   - **知乎 (Zhihu)**：官方网页端具有严苛的反爬风控，纯网页爬虫极易失败。本项目接入了官方知乎 CLI（数据开放平台原生接口），支持高质量的知乎搜索、全网搜索、热榜与直答。
   - **微博 (Weibo)**：原版未覆盖微博生态。本项目集成了 `weibo-cli`，支持热搜榜、博文正文、评论流及博主主页；同时针对其移动端搜索接口对 Cookie 容易失效报 `ok=-100` 的顽疾，自研内置了 `s_weibo_search.py` 网页解析脚本，实现高稳定的关键词检索。
   - **今日头条 (Toutiao)**：原版未覆盖头条体系。本项目全新研发 `s_toutiao.py`，专精于头条图文、微头条、评论流及实时热榜抓取。采用移动版 SSR 内嵌数据解析机制，**完全免登录、零凭证**即可直接读取正文与评论。
   - **雪球 (Xueqiu)**：新增雪球投资者社区适配（`snowball-cli`），支持个股 KOL 讨论流、全站热帖以及实时行情的备用兜底。
   - **豆瓣电影 (Douban)**：接入免登录的 Rexxar 移动端轻量接口，解决了桌面版页面对免 Cookie 请求的防爬拦截问题。

3. **国内生态与深度提取优化**
   - **微信文章解密与提取链**：内置专属 `wechat_search.py`，实现搜狗微信搜索结果与微信官方直链（`mp.weixin.qq.com`）的安全逆向解析；配合提取工具链实现 0.3s 级极速免登录正文抓取，避免无效消耗第三方付费渲染 API。
   - **小红书 xsec 机制打通**：完整覆盖小红书强制的 `xsec_token` 读取链路与风控避让策略。
   - **音视频转录链路增强**：`transcribe.py` 集成 Groq Whisper Large v3 云端极速转录能力，并针对小红书、B站、YouTube 提供结构化转文字与摘要规范输出。

4. **实战踩坑与运维指南（Operational Playbooks）**
   - 原版文档多停留在安装步骤，本项目在 `references/` 中记录了各平台真实对抗风控的落地经验（如 Chromium App-Bound Encryption 对 cookie 导出的影响、各平台的 Token 持久化与灾备恢复方案、CLI 在 Windows/PowerShell 下的执行陷阱等）。

---

## 🚀 一键安装与使用

无需手动找目录，也无需提前安装 Git 工具。直接把下面这句自然语言指令**复制发送给你的 Hermes Agent**：

```text
请帮我把这个 Skill 仓库安装到当前 profile 的 skills 目录下：
https://github.com/fenixggg/agent-reach-hermes
安装为 agent-reach 目录（优先用 git clone，若没有 git 则通过 GitHub API/ZIP 下载解压），完成后执行 /reload-skills 并确认是否就绪。
```

> **说明**：Hermes Agent 具备完备的代码执行与网络能力。即使你的环境里没有安装 `git` 命令行工具，Agent 也会自动通过 Python 或系统内置工具下载解压并挂载生效。

---

### 依赖 CLI 工具（完全解耦，按需安装）

该 Skill 采用模块化设计，平台 CLI **按需安装，互不影响**。即使你不安装任何 CLI，基础功能（如网页/微信文章直搜等）依然可用。当你需要特定平台时，甚至可以直接让 Agent 帮你在终端安装：

```bash
# 常用平台 Python CLI (可手动安装或让 Agent 帮装)
pipx install xiaohongshu-cli                          # 小红书
pipx install bilibili-cli                             # B站
pipx install kabi-weibo-cli                           # 微博 (weibo 命令)
pipx install twitter-cli                              # Twitter / X
pipx install "git+https://github.com/public-clis/rdt-cli.git" # Reddit

# 股票社区 (雪球)
npm install -g @snowball-tools/snowball-cli
```

---

### 🔑 凭据与环境变量配置

- **零配置开箱即用**：微信公众号搜索、V2EX 社区、豆瓣电影影评、B站免登录视频详情与原生字幕等，安装后**无需任何账号和凭据**即可直接使用。
- **需凭据的平台（智能引导）**：如需使用推特、知乎、Groq 音视频转录等需要鉴权的平台，**无需自己去翻看繁琐的接口文档**。本项目在 `references/` 目录中为每个平台编写了详尽的踩坑指引与维护说明。你只需在对话中对 Agent 说：
  > *“我想用 agent-reach 的知乎（或推特/小红书）功能，教我怎么配凭据？”*
  
  **Agent 会自动阅读对应平台的指南并一步步引导你获取和配置凭证**，遇到 Cookie 刷新、格式要求或权限坑点也会给出明确提示。

---

## 📂 目录结构

```text
agent-reach/
├── SKILL.md                 # 核心路由定义与使用指令
├── LICENSE                  # MIT 开源许可证
├── README.md                # 项目文档
├── references/              # 16 个平台的单独运维与最佳实践指导
│   ├── bilibili.md
│   ├── douban.md
│   ├── reddit.md
│   ├── twitter.md
│   ├── xiaohongshu.md
│   ├── xueqiu.md
│   ├── zhihu.md
│   └── ...
└── scripts/                 # 辅助脚本
    ├── wechat_search.py     # 微信公众号搜索与直链解析
    ├── transcribe.py        # 多平台音视频转文字稿
    └── transcribe_format.md # 转录文本格式规范
```

---

## ⚖️ 开源协议与鸣谢

- 本项目基于 [MIT License](LICENSE) 开源。
- 感谢 [Panniantong/Agent-Reach](https://github.com/Panniantong/Agent-Reach) 提供的灵感与原始架构设计。
