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
| **雪球 (Xueqiu)** | `snowball-cli` | 实时热帖、KOL观点、社区讨论 | 需 Cookie |
| **小红书 (XHS)** | `xhs-cli` | 笔记搜索、图文阅读（带 xsec） | 需本地 Cookie |
| **推特 / X** | `twitter-cli` | 推文读取、用户主页、时间线 | 需 Auth Token |
| **B站 (Bilibili)** | `bilibili-cli` | 视频详情、官方原生字幕提取、用户动态 | 公开只读免登录 |
| **Reddit** | `rdt-cli` | 帖子阅读、评论流、Subreddit 热门 | 需 Session / JWT |
| **微信公众号** | `wechat_search.py` | 搜狗微信直搜、落地真实 URL 解析 | 免登录 |
| **V2EX** | 官方公开 API | 节点主题、全站热门 | 免登录 |
| **豆瓣电影** | Rexxar API | 电影详情、影评、短评深度抓取 | 免登录 |
| **音视频转录** | `transcribe.py` (Whisper) | B站/YouTube/小红书音视频提取与 Groq 快速转录 | 需 Groq API Key |
| **GitHub / 开发** | `gh` CLI | 代码库检索、Issue/PR 联动 | 需 GitHub Auth |
| **网页全文阅读** | Jina / Firecrawl / better-webfetch | 通用正文提取与降噪 | 视选型而定 |

## 💡 与原版（Panniantong/Agent-Reach）的区别与改进

原版 `Agent-Reach` 主要是作为一个独立的全局 Python CLI 工具包来设计和分发的。而在实际接入 **Hermes Agent** 的高频对话与自动化调度场景中，直接运行原始仓库会面临上下文开销大、缺少原生平台规范、反爬机制适配等痛点。本项目基于此做了以下核心改进：

1. **架构改造：从通用 CLI 转换为 Hermes 原生 Skill 规范**
   - 彻底解耦庞大的单一代码库，改造为标准 Hermes Skill 结构（`SKILL.md` + 模块化 `references/` + 辅助 `scripts/`）。
   - **两层路由体系（节省 Context）**：Agent 在触发时仅需加载第一层轻量级索引，只有需要深入特定平台交互时才按需读取单项平台的 Markdown 文档，极大降低 Token 消耗。

2. **新增关键平台与官方 CLI 适配**
   - **知乎 (Zhihu)**：官方网页端具有严苛的反爬风控，纯网页爬虫极易失败。本项目接入了官方知乎 CLI（数据开放平台原生接口），支持高质量的知乎搜索、全网搜索、热榜与直答。
   - **雪球 (Xueqiu)**：新增雪球投资者社区适配（`snowball-cli`），支持个股 KOL 讨论流、全站热帖以及实时行情的备用兜底。
   - **豆瓣电影 (Douban)**：接入免登录的 Rexxar 移动端轻量接口，解决了桌面版页面对免 Cookie 请求的防爬拦截问题。

3. **国内生态与深度提取优化**
   - **微信文章解密与提取链**：内置专属 `wechat_search.py`，实现搜狗微信搜索结果与微信官方直链（`mp.weixin.qq.com`）的安全逆向解析；配合提取工具链实现 0.3s 级极速免登录正文抓取，避免无效消耗第三方付费渲染 API。
   - **小红书 xsec 机制打通**：完整覆盖小红书强制的 `xsec_token` 读取链路与风控避让策略。
   - **音视频转录链路增强**：`transcribe.py` 集成 Groq Whisper Large v3 云端极速转录能力，并针对小红书、B站、YouTube 提供结构化转文字与摘要规范输出。

4. **实战踩坑与运维指南（Operational Playbooks）**
   - 原版文档多停留在安装步骤，本项目在 `references/` 中记录了各平台真实对抗风控的落地经验（如 Chromium App-Bound Encryption 对 cookie 导出的影响、各平台的 Token 持久化与灾备恢复方案、CLI 在 Windows/PowerShell 下的执行陷阱等）。

---

## 🚀 安装与使用

### 1. 安装到 Hermes Agent
将本项目克隆到你的 Hermes profile skills 目录下：

```bash
# 进入你正在使用的 Hermes profiles/xxx/skills 目录
cd path/to/hermes-home/profiles/<your-profile>/skills/

# 克隆仓库
git clone https://github.com/fenixggg/agent-reach-hermes.git agent-reach
```

### 2. 依赖工具配置（按需安装）
根据你需要的平台，安装对应的开源 CLI 工具：

```bash
# Python 平台 CLI
pipx install xiaohongshu-cli
pipx install bilibili-cli
pipx install "git+https://github.com/public-clis/rdt-cli.git"
pipx install twitter-cli

# Node / npm 工具 (如有需要)
npm install -g @snowball-tools/snowball-cli
```

### 3. 配置环境变量 / 凭据
根据 `references/` 目录下各平台的文档指引，配置你的 `.env` 或本地 CLI 认证文件。常见凭据说明：
- **Groq API Key** (`GROQ_API_KEY`): 用于 `scripts/transcribe.py` 的音视频高速 Whisper 转录。
- **Twitter Token** (`TWITTER_AUTH_TOKEN`, `TWITTER_CT0`): 写入环境变量供 `twitter-cli` 读取。
- **知乎 Access Secret** (`ZHIHU_ACCESS_SECRET`): 供知乎官方 CLI 调用。

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
